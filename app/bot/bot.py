import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, Material

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self):
        self.bot = Bot(token=os.environ['TELEGRAM_BOT_TOKEN'])
        self.dp = Dispatcher()

        # Регистрация обработчиков
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.list_courses_handler, Command("courses"))
        self.dp.callback_query.register(self.course_callback_handler, lambda c: c.data.startswith('course_'))

    async def start_handler(self, message: types.Message):
        """Обработчик команды /start"""
        welcome_text = (
            "👋 Добро пожаловать в бот системы управления курсами!\n\n"
            "Доступные команды:\n"
            "/courses - Просмотр списка курсов\n"
        )
        await message.answer(welcome_text)

    async def list_courses_handler(self, message: types.Message):
        """Обработчик команды /courses"""
        courses = Course.query.all()
        if not courses:
            await message.answer("На данный момент нет доступных курсов.")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=course.title,
                callback_data=f"course_{course.id}"
            )]
            for course in courses
        ])

        await message.answer("Список доступных курсов:", reply_markup=keyboard)

    async def course_callback_handler(self, callback_query: types.CallbackQuery):
        """Обработчик выбора курса"""
        course_id = int(callback_query.data.split('_')[1])
        course = Course.query.get(course_id)

        if not course:
            await callback_query.answer("Курс не найден")
            return

        course_info = (
            f"📚 *{course.title}*\n"
            f"📝 {course.description}\n\n"
            "Материалы курса:\n"
        )

        for material in course.materials:
            course_info += f"📄 {material.title}\n"

        await callback_query.message.answer(course_info, parse_mode="Markdown")
        await callback_query.answer()

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")

course_bot = CourseBot()