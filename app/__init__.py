from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Инициализация расширений
    db.init_app(app)

    # Настройка Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'

    from app.routes import main, auth
    app.register_blueprint(main)
    app.register_blueprint(auth)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            logger.debug(f"[USER_LOADER] Loading user with ID: {user_id}")
            user = User.query.get(int(user_id))
            logger.debug(f"[USER_LOADER] User found: {user is not None}")
            if user:
                logger.debug(f"[USER_LOADER] User authenticated: {user.is_authenticated}")
            return user
        except Exception as e:
            logger.error(f"[USER_LOADER] Error loading user: {e}")
            return None

    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")

            # Создание администратора по умолчанию
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("Default admin user created successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise

    return app