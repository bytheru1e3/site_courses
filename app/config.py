import os
import secrets
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

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
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "7884948980:AAFSmEjRYMvE-tgv82wWquqd2v0_L6C-Pd8")