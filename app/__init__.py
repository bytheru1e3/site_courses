from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
import os
from flask_login import LoginManager

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Инициализация расширений
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Загрузка конфигурации
    from app.config import Config
    app.config.from_object(Config)

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)

    # Регистрация блюпринтов
    from app.routes import main
    from app.admin import admin
    from app.api import api

    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)

    # Регистрация обработчика для login_manager
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Создание таблиц базы данных
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            db.session.rollback()

    return app