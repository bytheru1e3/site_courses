import asyncio
import logging
import os
from app.bot.bot import CourseBot
from app import create_app, db
from app.models import Course
from sqlalchemy import text

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_database():
    """Проверка подключения к базе данных"""
    try:
        # Проверяем подключение к базе данных
        result = db.session.execute(text('SELECT 1'))
        result.scalar()

        # Проверяем наличие таблицы courses и получаем количество курсов
        courses_count = Course.query.count()
        logger.info(f"Database connection successful. Found {courses_count} courses.")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        return False

async def main():
    """Основная функция запуска бота"""
    try:
        # Создаем приложение Flask
        app = create_app()
        logger.info("Flask application created successfully")

        # Активируем контекст приложения
        with app.app_context():
            logger.info("Flask application context activated")

            # Проверяем подключение к базе данных перед запуском бота
            if not await check_database():
                logger.error("Failed to connect to database. Exiting...")
                return

            # Проверяем наличие токена Telegram
            if not os.environ.get('TELEGRAM_BOT_TOKEN'):
                logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
                return

            try:
                # Создаем экземпляр бота с приложением Flask
                course_bot = CourseBot(app=app)
                logger.info("Created CourseBot instance successfully")

                # Запускаем бота
                logger.info("Starting Telegram bot polling...")
                await course_bot.start_polling()
            except Exception as e:
                logger.error(f"Error in bot execution: {e}", exc_info=True)
                raise

    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
        raise
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error in bot execution: {e}", exc_info=True)