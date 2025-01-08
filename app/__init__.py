from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging

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
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'

    # Функция загрузки пользователя для Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        try:
            from app.models import User
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error loading user: {e}")
            return None

    # Регистрация блюпринтов
    from app.routes import main
    from app.auth import auth
    from app.api import api
    from app.admin import admin

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(api)
    app.register_blueprint(admin)

    # Создание таблиц базы данных и администратора по умолчанию
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")

            # Создание администратора по умолчанию
            from app.models import User
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    is_admin=True
                )
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("Default admin user created")

        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            db.session.rollback()

    return app