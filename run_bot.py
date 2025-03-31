import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app.bot.bot import CourseBot

if __name__ == "__main__":
    bot = CourseBot()
    asyncio.run(bot.start_polling())