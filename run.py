import os
import logging
import threading
from app import create_app
from app.bot.bot import CourseBot

# Настройка логирования (Reusing from original code, but now within the edited structure)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot(app):
    """Запуск Telegram бота в отдельном потоке"""
    try:
        # Создаем и запускаем бота
        bot = CourseBot(app)
        logger.info("Bot instance created successfully")
        bot.start_polling()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

def main():
    """Основная функция запуска приложения"""
    try:
        # Создаем Flask приложение
        app = create_app()
        logger.info("Flask application created successfully")

        # Запускаем бота в отдельном потоке
        bot_thread = threading.Thread(target=run_bot, args=(app,))
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("Bot thread started successfully")

        # Запускаем Flask приложение
        logger.info("Starting Flask application...")
        return app

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

if __name__ == '__main__':
    try:
        app = main()
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")