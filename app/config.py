import os
from dotenv import load_dotenv
import secrets

load_dotenv()

class Config:
    # Генерируем стабильный secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    # Настройки сессии
    SESSION_PROTECTION = 'strong'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 минут
    SESSION_TYPE = 'filesystem'
    # Дополнительные настройки безопасности
    REMEMBER_COOKIE_DURATION = 1800  # 30 минут
    REMEMBER_COOKIE_SECURE = False  # В продакшене должно быть True
    REMEMBER_COOKIE_HTTPONLY = True