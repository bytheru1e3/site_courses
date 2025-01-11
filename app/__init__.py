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

    # Создаем необходимые директории
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['VECTOR_DB_PATH'], exist_ok=True)

    # Инициализация расширений
    db.init_app(app)

    # Регистрация блюпринтов
    from app.routes import main
    app.register_blueprint(main)
    from app.admin import admin
    app.register_blueprint(admin)
    from app.api import api
    app.register_blueprint(api)
    from app.api.telegram import telegram_api
    app.register_blueprint(telegram_api)


    # Создание таблиц базы данных
    with app.app_context():
        try:
            # Import models here to ensure they are registered with SQLAlchemy
            from app.models import User, Course, Material, MaterialFile, Notification
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise

    return app