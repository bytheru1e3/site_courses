import os
import secrets

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Basic security settings for development
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

    # Telegram
    TELEGRAM_BOT_TOKEN = "7884948980:AAFSmEjRYMvE-tgv82wWquqd2v0_L6C-Pd8"
    TELEGRAM_CHAT_ID = "-4585100175"