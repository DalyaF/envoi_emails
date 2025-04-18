# 📧 Script d'envoi d'emails automatiques avec Python

## 🎯 Objectif

Automatiser l'envoi d'emails (newsletters, confirmations, etc.) via SMTP à partir d'une liste de contacts.

## 🧰 Stack technique

- **Python**
  - `smtplib` pour l'envoi d'emails
  - `argparse` pour les options en ligne de commande
- **Sources de données** : 
  - Fichier CSV
  - Base de données SQLite

## ⚙️ Fonctionnalités

- Chargement des contacts depuis un fichier CSV ou une base SQLite
- Personnalisation des emails à l'aide de modèles HTML et/ou texte
- Envoi via un serveur SMTP (Gmail, etc.)
- Gestion du délai entre les envois
- Mode test pour limiter à 3 emails
- Requête SQL personnalisée (pour affiner la sélection de contacts depuis SQLite)

## 🚀 Utilisation

```bash
python envoi_emails.py \
  --source csv \
  --source-file contacts.csv \
  --template template.html \
  --subject "Bonjour {{ nom }}" \
  --from "votre.email@domaine.com" \
  --smtp-server smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user votre.email@domaine.com \
  --smtp-password votre_mot_de_passe_app \
  --delay 5 \
  --test

