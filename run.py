from app import create_app, db
from app.bot.bot import CourseBot
from app.config import Config
import os
from dotenv import load_dotenv
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = create_app()

async def run_bot():
    """Асинхронный запуск бота"""
    try:
        bot_token = Config.TELEGRAM_BOT_TOKEN
        if not bot_token:
            logger.error("Telegram bot token not found in configuration")
            return

        bot = CourseBot(bot_token)
        logger.info("Starting Telegram bot")
        await bot.run_polling()
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")

def run_flask():
    """Запуск Flask приложения"""
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

async def main():
    """Основная функция для запуска всех компонентов"""
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

    # Создаем и запускаем задачи
    bot_task = asyncio.create_task(run_bot())
    flask_task = asyncio.get_event_loop().run_in_executor(None, run_flask)

    # Ждем завершения обеих задач
    await asyncio.gather(bot_task, flask_task)

if __name__ == '__main__':
    # Запускаем основной цикл событий
    asyncio.run(main())