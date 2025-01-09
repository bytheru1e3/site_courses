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
    try:
        app = Flask(__name__)
        logger.info("Flask application instance created")

        # Настройка конфигурации
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }

        # Создание необходимых директорий
        os.makedirs(os.path.join(app.root_path, 'data'), exist_ok=True)  # Для векторной базы данных
        os.makedirs(os.path.join(app.root_path, 'uploads'), exist_ok=True)  # Для загруженных файлов
        os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)  # Для шаблонов
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
                logger.error(f"Error during database initialization: {e}")
                db.session.rollback()
                raise

        # Регистрация блюпринтов
        try:
            logger.info("Registering blueprints...")
            from app.routes import main
            app.register_blueprint(main)
            logger.info("Blueprints registered successfully")
        except Exception as e:
            logger.error(f"Error registering blueprints: {e}")
            raise

        return app
    except Exception as e:
        logger.error(f"Failed to create Flask application: {e}", exc_info=True)
        raise