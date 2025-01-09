import asyncio
import logging
from app.bot.bot import course_bot
from app import create_app

# Создаем приложение для контекста
app = create_app()

async def main():
    with app.app_context():
        await course_bot.start_polling()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
