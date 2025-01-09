import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определение базового класса для моделей
class Base(DeclarativeBase):
    pass

# Инициализация расширений
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    logger.info("Starting application initialization...")
    app = Flask(__name__)
    logger.info("Flask application instance created")

    # Загрузка конфигурации
    from app.config import Config
    app.config.from_object(Config)
    logger.info("Configuration loaded")

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    logger.info("Extensions initialized")

    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static'), exist_ok=True)
    logger.info("Required directories created")

    # Регистрация обработчика для login_manager
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    with app.app_context():
        # Импорт моделей
        from app.models import User, Course, Material, MaterialFile, Notification
        logger.info("Models imported")

        # Создание таблиц
        try:
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

        # Регистрация блюпринтов
        try:
            from app.routes import main
            from app.admin import admin
            from app.auth import auth

            app.register_blueprint(main)
            app.register_blueprint(admin)
            app.register_blueprint(auth)
            logger.info("Blueprints registered")
        except Exception as e:
            logger.error(f"Error registering blueprints: {e}")
            raise

    logger.info("Application initialization completed")
    return app