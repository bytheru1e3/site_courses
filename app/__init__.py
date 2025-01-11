from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Инициализация расширений
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Загрузка конфигурации
    from app.config import Config
    app.config.from_object(Config)

    # Инициализация расширений
    db.init_app(app)

    # Регистрация блюпринтов
    from app.routes import main
    from app.admin import admin
    from app.api import api
    from app.api.telegram import telegram_api  # Добавляем новый blueprint

    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    app.register_blueprint(telegram_api)  # Регистрируем новый blueprint

    # Создание таблиц базы данных
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            db.session.rollback()

    return app