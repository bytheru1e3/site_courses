import os
import logging
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self, token, api_url):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.api_url = api_url

        # Регистрация обработчиков
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.callback_query.register(self.handle_course_callback, F.data.startswith("course:"))

    async def start_handler(self, message: types.Message):
        """Обработчик команды /start"""
        try:
            response = requests.get(f"{self.api_url}/api/courses")
            data = response.json()

            if not data.get('success'):
                await message.answer("Ошибка при получении курсов. Попробуйте позже.")
                return

            courses = data.get('courses', [])
            if not courses:
                await message.answer("На данный момент нет доступных курсов.")
                return

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=course['title'],
                    callback_data=f"course:{course['id']}"
                )]
                for course in courses
            ])

            await message.answer(
                "Список доступных курсов:",
                reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error in start_handler: {e}")
            await message.answer("Произошла ошибка при получении курсов.")

    async def handle_course_callback(self, callback_query: types.CallbackQuery):
        """Обработчик выбора курса"""
        try:
            course_id = int(callback_query.data.split(":")[1])
            response = requests.get(f"{self.api_url}/api/courses/{course_id}")
            data = response.json()

            if not data.get('success'):
                await callback_query.message.answer("Ошибка при получении информации о курсе.")
                return

            course = data.get('course', {})
            course_info = (
                f"📚 *{course['title']}*\n\n"
                f"📝 {course['description']}\n\n"
                "Доступные материалы:\n"
            )

            for material in course.get('materials', []):
                course_info += f"- {material['title']}\n"

            await callback_query.message.answer(
                course_info,
                parse_mode="Markdown"
            )
            await callback_query.answer()

        except Exception as e:
            logger.error(f"Error in handle_course_callback: {e}")
            await callback_query.message.answer("Произошла ошибка при получении информации о курсе.")
            await callback_query.answer()

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
