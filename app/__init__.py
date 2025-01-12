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
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
        from app.admin import admin

        app.register_blueprint(main)
        app.register_blueprint(admin)

        # Создание администратора по умолчанию (kept for potential future use, could be removed)
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