from app import create_app, db
from app.bot.bot import CourseBot
from app.config import Config
import os
from dotenv import load_dotenv
import logging
import asyncio
from threading import Thread

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
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("Default admin user created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def run_flask():
    """Запуск Flask приложения"""
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Error running Flask app: {e}")
        raise

def run_bot_forever():
    """Запуск бота в отдельном потоке с собственным циклом событий"""
    try:
        bot_token = Config.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.error("Telegram bot token not found")
            return

        logger.info("Initializing Telegram bot...")
        bot = CourseBot(bot_token)

        # Создаем новый цикл событий для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Запускаем бота
        logger.info("Starting bot polling...")
        loop.run_until_complete(bot.run_polling())
    except Exception as e:
        logger.error(f"Error in bot thread: {e}")
        raise
    finally:
        loop.close()

if __name__ == '__main__':
    try:
        # Инициализация базы данных
        init_database()

        # Запуск Flask в основном потоке
        flask_thread = Thread(target=run_flask)
        flask_thread.start()

        # Запуск бота в отдельном потоке
        bot_thread = Thread(target=run_bot_forever)
        bot_thread.daemon = True  # Поток бота будет завершен при выходе из программы
        bot_thread.start()

        # Ожидаем завершения Flask
        flask_thread.join()

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")