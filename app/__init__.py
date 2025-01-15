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
    app = Flask(__name__)

    # Загрузка конфигурации
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'

    with app.app_context():
        # Создание необходимых директорий
        uploads_dir = os.path.join(app.root_path, 'uploads')
        data_dir = os.path.join(app.root_path, 'data')
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # Создание таблиц базы данных
        try:
            # Import models here to ensure they are registered with SQLAlchemy
            from app.models import User, Course, Material, MaterialFile  # noqa: F401
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            db.session.rollback()

        # Регистрация блюпринтов
        from app.routes import main
        app.register_blueprint(main)

        logger.info("Application initialized successfully")
        return app

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))