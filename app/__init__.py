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
    app.config["LOGIN_DISABLED"] = True  # Отключаем обязательную авторизацию

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = None  # Отключаем редирект на страницу логина

    with app.app_context():
        # Создание необходимых директорий
        uploads_dir = os.path.join(app.root_path, 'uploads')
        data_dir = os.path.join(app.root_path, 'data')
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # Инициализация базы данных
        try:
            from app.models import Course, User, Material, MaterialFile, Notification
            db.create_all()
            logger.info("Database tables created successfully")

            # Создаем тестового админа если его нет
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    is_admin=True,
                    telegram_id='12345'  # Добавляем тестовый telegram_id
                )
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created successfully")

            # Создаем тестовый курс если нет курсов
            if not Course.query.first():
                test_course = Course(
                    title='Тестовый курс',
                    description='Это тестовый курс для проверки функциональности системы',
                    user_id=admin.id
                )
                db.session.add(test_course)

                # Добавляем тестовый материал
                test_material = Material(
                    course_id=test_course.id,
                    title='Введение',
                    content='Это вводный материал тестового курса.'
                )
                db.session.add(test_material)
                db.session.commit()
                logger.info("Test course and material created successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            db.session.rollback()

        # Регистрация блюпринтов
        from app.routes import main
        app.register_blueprint(main)

        from app.api import api
        app.register_blueprint(api)

        from app.api.telegram import telegram_api
        app.register_blueprint(telegram_api)

        @login_manager.user_loader
        def load_user(user_id):
            try:
                from app.models import User
                return User.query.get(int(user_id))
            except Exception as e:
                logger.error(f"Error loading user: {e}")
                return None

        logger.info("Application initialized successfully")
        return app