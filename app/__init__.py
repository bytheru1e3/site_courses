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

    # Настройка подключения к базе данных с SSL параметрами
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Добавляем параметры SSL и пула соединений
        if '?' in db_url:
            db_url += '&'
        else:
            db_url += '?'
        db_url += 'sslmode=require'

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        'pool_pre_ping': True,  # Проверка соединения перед использованием
        'pool_recycle': 280,    # Пересоздание соединений каждые 280 секунд
        'pool_timeout': 30,     # Таймаут ожидания соединения из пула
        'pool_size': 30,        # Максимальный размер пула
        'max_overflow': 10,     # Максимальное количество дополнительных соединений
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 10
        }
    }

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

        app.register_blueprint(main)
        app.register_blueprint(admin)
        app.register_blueprint(auth)

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