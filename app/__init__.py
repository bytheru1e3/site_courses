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

def create_app():
    try:
        app = Flask(__name__)
        logger.info("Flask application instance created")

        # Импортируем конфигурацию здесь, чтобы избежать циклического импорта
        from app.config import Config
        app.config.from_object(Config)

        # Создание необходимых директорий
        os.makedirs(os.path.join(app.root_path, 'data'), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, 'uploads'), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)
        logger.info("Required directories created")

        # Инициализация расширений
        db.init_app(app)
        login_manager.init_app(app)
        logger.info("Extensions initialized")

        # Регистрация обработчика для login_manager
        @login_manager.user_loader
        def load_user(user_id):
            from app.models import User
            return User.query.get(int(user_id))

        # Создание таблиц базы данных внутри контекста приложения
        with app.app_context():
            try:
                logger.info("Creating database tables...")
                db.create_all()
                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error(f"Error during database initialization: {str(e)}")
                db.session.rollback()
                raise

        # Регистрация блюпринтов
        try:
            logger.info("Registering blueprints...")
            from app.routes import main
            app.register_blueprint(main)
            logger.info("Blueprints registered successfully")
        except Exception as e:
            logger.error(f"Error registering blueprints: {str(e)}")
            raise

        return app
    except Exception as e:
        logger.error(f"Failed to create Flask application: {str(e)}", exc_info=True)
        raise