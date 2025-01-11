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

    with app.app_context():
        # Импорт моделей для создания таблиц
        from app.models import User, Course, Material, MaterialFile, Notification

        # Создание таблиц базы данных
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            db.session.rollback()

        # Регистрация блюпринтов
        from app.routes import main
        app.register_blueprint(main)

    return app