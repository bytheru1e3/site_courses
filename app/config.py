import os
import secrets
from datetime import timedelta

class Config:
    # Генерируем стабильный secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Flask-Login
    SESSION_PROTECTION = None  # Отключаем временно для отладки
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)  # Увеличиваем время жизни сессии
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False  # В development окружении отключаем HTTPS
    SESSION_COOKIE_SECURE = False   # В development окружении отключаем HTTPS

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')