from app import create_app, db
from app.bot.bot import CourseBot
import os
from dotenv import load_dotenv
import threading
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = create_app()

def run_bot():
    """Запуск Telegram бота в отдельном потоке"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return

        bot = CourseBot(bot_token)
        logger.info("Starting Telegram bot")
        bot.run()
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")

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
                try:
                    admin = User(username='admin', is_admin=True)
                    admin.set_password('admin')
                    db.session.add(admin)
                    db.session.commit()
                    logger.info("Default admin user created successfully")
                except Exception as e:
                    logger.error(f"Error creating default admin user: {e}")
                    db.session.rollback()
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Bot thread started")

    # Запуск Flask приложения
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )