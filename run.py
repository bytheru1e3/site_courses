from app import create_app, db
from app.bot.bot import CourseBot
from app.config import Config
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

def run_bot_forever():
    """Запуск бота в отдельном потоке с собственным event loop"""
    try:
        # Создаем новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        bot_token = Config.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.error("Telegram bot token not found in configuration")
            return

        bot = CourseBot(bot_token)
        logger.info("Starting Telegram bot")

        # Запускаем бота в event loop
        loop.run_until_complete(bot.run_polling())
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")
    finally:
        loop.close()

if __name__ == '__main__':
    with app.app_context():
        # Создание таблиц базы данных
        try:
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
            logger.error(f"Error creating database tables: {e}")
            raise

    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot_forever)
    bot_thread.daemon = True  # Поток завершится вместе с основной программой
    bot_thread.start()
    logger.info("Telegram bot thread started")

    # Запуск Flask приложения
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )