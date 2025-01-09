import asyncio
import logging
from app.bot.bot import course_bot
from app import create_app, db
from app.models import Course

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем приложение для контекста
app = create_app()

async def check_database():
    """Проверка подключения к базе данных"""
    try:
        with app.app_context():
            # Проверяем подключение к базе данных
            db.session.execute('SELECT 1')
            # Проверяем наличие таблицы courses
            courses_count = Course.query.count()
            logger.info(f"Database connection successful. Found {courses_count} courses.")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

async def main():
    try:
        # Проверяем подключение к базе данных перед запуском бота
        if not await check_database():
            logger.error("Failed to connect to database. Exiting...")
            return

        with app.app_context():
            logger.info("Starting Telegram bot with Flask context...")
            await course_bot.start_polling()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Critical error in bot execution: {e}", exc_info=True)