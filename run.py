from app import create_app, db
from app.bot.bot import CourseBot
import os
from dotenv import load_dotenv
import logging
import asyncio
import threading

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = create_app()

def init_database():
    """Инициализация базы данных"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")

            # Создание администратора по умолчанию, если его нет
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
                logger.info("Default admin user created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def run_bot():
    """Запуск бота в отдельном потоке"""
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return

        # В development используем localhost, в production нужно будет изменить
        api_url = f"http://localhost:{os.environ.get('PORT', 5000)}"

        bot = CourseBot(bot_token, api_url)
        asyncio.run(bot.start_polling())
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == '__main__':
    try:
        # Инициализация базы данных
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")

        # Запуск бота в отдельном потоке
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()

        # Запуск Flask приложения
        app.run(host='0.0.0.0', port=5000, debug=True)

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")