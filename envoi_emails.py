import smtplib
import csv
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template
import time
import logging
import argparse
import os
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("email_sender.log"),
        logging.StreamHandler()
    ]
)

class EmailSender:
    def __init__(self, server, port, username, password):
        """Initialisation avec les informations du serveur SMTP"""
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.smtp_session = None
        
    def connect(self):
        """Établit la connexion au serveur SMTP"""
        try:
            self.smtp_session = smtplib.SMTP(self.server, self.port)
            self.smtp_session.ehlo()
            self.smtp_session.starttls()
            self.smtp_session.login(self.username, self.password)
            logging.info("Connexion SMTP établie avec succès")
            return True
        except Exception as e:
            logging.error(f"Erreur de connexion SMTP: {str(e)}")
            return False
            
    def disconnect(self):
        """Ferme la connexion SMTP"""
        if self.smtp_session:
            self.smtp_session.quit()
            logging.info("Déconnexion SMTP réussie")
            
    def send_email(self, from_email, to_email, subject, message_html, message_text=None):
        """Envoie un seul email"""
        if not self.smtp_session:
            if not self.connect():
                return False
                
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Version texte (facultative)
            if message_text:
                msg.attach(MIMEText(message_text, 'plain'))
                
            # Version HTML (obligatoire dans notre cas)
            msg.attach(MIMEText(message_html, 'html'))
            
            self.smtp_session.send_message(msg)
            logging.info(f"Email envoyé à {to_email}")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'email à {to_email}: {str(e)}")
            return False

class ContactManager:
    @staticmethod
    def get_contacts_from_csv(csv_file):
        """Charge les contacts depuis un fichier CSV"""
        contacts = []
        try:
            with open(csv_file, 'r', encoding='ISO-8859-1') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    contacts.append(row)
            logging.info(f"Chargement de {len(contacts)} contacts depuis {csv_file}")
            return contacts
        except Exception as e:
            logging.error(f"Erreur lors du chargement du fichier CSV: {str(e)}")
            return []
    
    @staticmethod
    def get_contacts_from_sqlite(db_file, query=None):
        """Charge les contacts depuis une base SQLite"""
        if query is None:
            query = "SELECT * FROM contacts WHERE active = 1"
            
        contacts = []
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Récupération des noms de colonnes
            column_names = [description[0] for description in cursor.description]
            
            # Conversion des résultats en dictionnaires
            for row in cursor.fetchall():
                contact = dict(zip(column_names, row))
                contacts.append(contact)
                
            conn.close()
            logging.info(f"Chargement de {len(contacts)} contacts depuis la base SQLite")
            return contacts
        except Exception as e:
            logging.error(f"Erreur lors de la connexion à la base SQLite: {str(e)}")
            return []

class TemplateManager:
    @staticmethod
    def load_template(template_file):
        """Charge un modèle d'email depuis un fichier"""
        try:
            with open(template_file, 'r', encoding='ISO-8859-1') as file:
                template_content = file.read()
            return template_content
        except Exception as e:
            logging.error(f"Erreur lors du chargement du modèle: {str(e)}")
            return None
    
    @staticmethod
    def personalize_message(template_content, contact_data):
        """Personnalise le message avec les données du contact"""
        try:
            template = Template(template_content)
            return template.safe_substitute(contact_data)
        except Exception as e:
            logging.error(f"Erreur lors de la personnalisation du message: {str(e)}")
            return None

def send_bulk_emails(email_sender, from_email, contacts, subject_template, html_template, 
                    text_template=None, delay=5, test_mode=False, max_emails=None):
    """Fonction principale pour l'envoi massif d'emails"""
    
    sent_count = 0
    failed_count = 0
    
    # Limiter le nombre d'emails si en mode test
    if test_mode and (max_emails is None or max_emails > 3):
        max_emails = 3
        logging.info("Mode test activé: envoi limité à 3 emails")
    
    total_emails = len(contacts)
    if max_emails is not None:
        total_emails = min(total_emails, max_emails)
    
    logging.info(f"Début de l'envoi de {total_emails} emails")
    
    for i, contact in enumerate(contacts):
        if max_emails is not None and i >= max_emails:
            break
            
        # Personnalisation du sujet
        subject = Template(subject_template).safe_substitute(contact)
        
        # Personnalisation du message HTML
        html_message = TemplateManager.personalize_message(html_template, contact)
        
        # Personnalisation du message texte (facultatif)
        text_message = None
        if text_template:
            text_message = TemplateManager.personalize_message(text_template, contact)
        
        # Envoi de l'email
        recipient = contact.get('email')
        if not recipient:
            logging.warning(f"Contact {i+1} sans adresse email, ignoré")
            failed_count += 1
            continue
            
        success = email_sender.send_email(
            from_email, 
            recipient,
            subject,
            html_message,
            text_message
        )
        
        if success:
            sent_count += 1
        else:
            failed_count += 1
            
        # Pause entre les envois pour éviter d'être flaggé comme spam
        if i < total_emails - 1 and delay > 0:
            time.sleep(delay)
    
    logging.info(f"Envoi terminé: {sent_count} emails envoyés, {failed_count} échecs")
    return sent_count, failed_count

def main():
    parser = argparse.ArgumentParser(description="Outil d'envoi d'emails automatiques")
    parser.add_argument('--source', choices=['csv', 'sqlite'], required=True, 
                        help="Source des contacts (csv ou sqlite)")
    parser.add_argument('--source-file', required=True, 
                        help="Fichier CSV ou base de données SQLite")
    parser.add_argument('--template', required=True, 
                        help="Fichier de modèle HTML pour l'email")
    parser.add_argument('--text-template', 
                        help="Fichier de modèle texte (facultatif)")
    parser.add_argument('--subject', required=True, 
                        help="Sujet de l'email (peut contenir des variables)")
    parser.add_argument('--from', dest='from_email', required=True, 
                        help="Adresse email d'expédition")
    parser.add_argument('--smtp-server', required=True, 
                        help="Serveur SMTP")
    parser.add_argument('--smtp-port', type=int, default=587, 
                        help="Port SMTP (par défaut: 587)")
    parser.add_argument('--smtp-user', required=True, 
                        help="Nom d'utilisateur SMTP")
    parser.add_argument('--smtp-password', required=True, 
                        help="Mot de passe SMTP")
    parser.add_argument('--delay', type=int, default=5, 
                        help="Délai entre les envois en secondes (par défaut: 5)")
    parser.add_argument('--max-emails', type=int, 
                        help="Nombre maximum d'emails à envoyer")
    parser.add_argument('--test', action='store_true', 
                        help="Mode test (envoie seulement 3 emails)")
    parser.add_argument('--query', 
                        help="Requête SQL personnalisée (pour source SQLite)")
    
    args = parser.parse_args()
    
    # Chargement du modèle HTML
    html_template = TemplateManager.load_template(args.template)
    if not html_template:
        logging.error("Impossible de charger le modèle HTML")
        return
    
    # Chargement du modèle texte (facultatif)
    text_template = None
    if args.text_template:
        text_template = TemplateManager.load_template(args.text_template)
    
    # Chargement des contacts
    contacts = []
    if args.source == 'csv':
        contacts = ContactManager.get_contacts_from_csv(args.source_file)
    elif args.source == 'sqlite':
        contacts = ContactManager.get_contacts_from_sqlite(args.source_file, args.query)
    
    if not contacts:
        logging.error("Aucun contact chargé")
        return
    
    # Initialisation de l'expéditeur d'emails
    email_sender = EmailSender(
        args.smtp_server,
        args.smtp_port,
        args.smtp_user,
        args.smtp_password
    )
    
    # Envoi des emails
    try:
        send_bulk_emails(
            email_sender,
            args.from_email,
            contacts,
            args.subject,
            html_template,
            text_template,
            args.delay,
            args.test,
            args.max_emails
        )
    finally:
        # Fermeture de la connexion SMTP
        email_sender.disconnect()

if __name__ == "__main__":
    start_time = datetime.now()
    main()
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Exécution terminée en {duration}")