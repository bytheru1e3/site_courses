import os
import logging
from app import create_app

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска приложения"""
    try:
        # Создаем Flask приложение
        app = create_app()
        logger.info("Flask application created successfully")
        
        # Импортируем здесь, чтобы избежать циклических импортов
        from app.bot.bot import CourseBot

        # Создаем и запускаем бота
        bot = CourseBot(app)
        logger.info("Bot instance created successfully")
        bot.start_polling() #Start polling directly

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