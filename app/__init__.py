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
    from app.config import Config
    app.config.from_object(Config)

    # Создаем необходимые директории
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'app/uploads'), exist_ok=True)
    os.makedirs(app.config.get('VECTOR_DB_PATH', 'app/data/vector_store'), exist_ok=True)

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Регистрация блюпринтов
    with app.app_context():
        from app.routes import main
        app.register_blueprint(main)

        try:
            # Import models here to ensure they are registered with SQLAlchemy
            from app.models import User, Course, Material, MaterialFile, Notification
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise

    return app