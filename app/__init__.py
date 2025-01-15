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

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

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
        from app.admin import admin
        from app.auth import auth
        from app.api.telegram import telegram_api

        app.register_blueprint(main)
        app.register_blueprint(admin)
        app.register_blueprint(auth)
        app.register_blueprint(telegram_api)

        # Создание администратора по умолчанию
        try:
            admin_exists = User.query.filter_by(username="admin").first()
            if not admin_exists:
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    is_admin=True
                )
                admin_user.set_password("admin")
                db.session.add(admin_user)
                db.session.commit()
                logger.info("Default admin user created")
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")
            db.session.rollback()

    return app