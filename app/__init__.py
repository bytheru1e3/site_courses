from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Инициализация расширений
db = SQLAlchemy()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def create_app():
    """Фабрика создания Flask приложения"""
    app = Flask(__name__)

    # Загрузка конфигурации
    from app.config import Config
    app.config.from_object(Config)

    # Создаем директории если их нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    with app.app_context():
        # Импорт моделей здесь, чтобы избежать циклических импортов
        from app.models import User, Course, Material, MaterialFile, Notification

        # Создание таблиц
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

        # Регистрация блюпринтов
        try:
            from app.routes import main
            app.register_blueprint(main)

            from app.api import api
            app.register_blueprint(api, url_prefix='/api')

            logger.info("All blueprints registered successfully")

        except Exception as e:
            logger.error(f"Error registering blueprints: {e}")
            raise

    return app