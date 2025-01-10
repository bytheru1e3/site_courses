import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.enums import ParseMode
from app.models import Course
from flask import Flask

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self, app: Flask):
        """Инициализация бота"""
        if not app:
            raise ValueError("Flask application must be provided")

        self.app = app
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

        # Dictionary to store user's current course selection
        self.user_states = {}

        logger.info("Initializing Telegram bot...")
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()
        self._register_handlers()
        logger.info("Bot handlers registered successfully")

    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        try:
            # Basic commands
            self.dp.message.register(self.start_handler, Command("start"))
            self.dp.message.register(self.help_handler, Command("help"))
            self.dp.message.register(self.list_courses_handler, Command("courses"))
            self.dp.message.register(self.chat_handler, Command("chat"))

            # Callback handlers
            self.dp.callback_query.register(
                self.course_callback_handler,
                lambda c: c.data and c.data.startswith('course_')
            )
            self.dp.callback_query.register(
                self.chat_course_callback_handler,
                lambda c: c.data and c.data.startswith('chat_course_')
            )

            # General message handler
            self.dp.message.register(self.handle_message)

            logger.info("All handlers registered successfully")
        except Exception as e:
            logger.error(f"Error registering handlers: {e}")
            raise

    async def setup_bot_commands(self):
        """Настройка команд бота"""
        commands = [
            BotCommand(command="start", description="🚀 Начать работу"),
            BotCommand(command="help", description="ℹ️ Помощь"),
            BotCommand(command="courses", description="📚 Список курсов"),
            BotCommand(command="chat", description="💬 Задать вопрос")
        ]
        await self.bot.set_my_commands(commands)
        logger.info("Bot commands menu has been set up")

    async def start_handler(self, message: Message):
        """Обработчик команды /start"""
        welcome_text = (
            "👋 Добро пожаловать в бот системы управления курсами!\n\n"
            "Доступные команды:\n"
            "/courses - Просмотр списка курсов\n"
            "/chat - Начать чат с ассистентом\n"
            "/help - Помощь и информация"
        )
        await message.answer(welcome_text)

    async def help_handler(self, message: Message):
        """Обработчик команды /help"""
        help_text = (
            "🔍 Справка по использованию бота:\n\n"
            "1️⃣ /start - Начать работу с ботом\n"
            "2️⃣ /courses - Показать список доступных курсов\n"
            "3️⃣ /chat - Начать чат с ассистентом\n"
            "4️⃣ /help - Показать это сообщение\n\n"
            "После выбора курса вы сможете:\n"
            "📚 Просматривать материалы курса\n"
            "💬 Задавать вопросы по материалам"
        )
        await message.answer(help_text)

    async def list_courses_handler(self, message: Message):
        """Обработчик команды /courses"""
        try:
            with self.app.app_context():
                courses = Course.query.all()
                if not courses:
                    await message.answer("📚 На данный момент нет доступных курсов")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"course_{course.id}"
                    )]
                    for course in courses
                ])

                await message.answer("📚 Список доступных курсов:", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error in list_courses handler: {e}")
            await message.answer("❌ Произошла ошибка при получении списка курсов")

    async def chat_handler(self, message: Message):
        """Обработчик команды /chat"""
        try:
            with self.app.app_context():
                courses = Course.query.all()
                if not courses:
                    await message.answer("📚 На данный момент нет доступных курсов")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"chat_course_{course.id}"
                    )]
                    for course in courses
                ])

                await message.answer(
                    "Выберите курс, по которому хотите задать вопрос:",
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            await message.answer("❌ Произошла ошибка при запуске чата")

    async def course_callback_handler(self, callback_query: CallbackQuery):
        """Обработчик выбора курса"""
        try:
            course_id = int(callback_query.data.split('_')[1])
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback_query.answer("❌ Курс не найден")
                    return

                course_info = (
                    f"*{course.title}*\n"
                    f"{course.description or 'Описание отсутствует'}"
                )

                await callback_query.message.answer(course_info, parse_mode=ParseMode.MARKDOWN)
                await callback_query.answer()
        except Exception as e:
            logger.error(f"Error in course callback handler: {e}")
            await callback_query.answer("❌ Произошла ошибка при получении информации о курсе")

    async def chat_course_callback_handler(self, callback_query: CallbackQuery):
        """Обработчик выбора курса для чата"""
        try:
            user_id = callback_query.from_user.id
            course_id = int(callback_query.data.split('_')[2])

            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback_query.answer("❌ Курс не найден")
                    return

                self.user_states[user_id] = {'selected_course': course_id}
                await callback_query.message.answer(
                    f"Вы выбрали курс: *{course.title}*\n"
                    "Теперь вы можете задать свой вопрос.",
                    parse_mode=ParseMode.MARKDOWN
                )
                await callback_query.answer()
        except Exception as e:
            logger.error(f"Error in chat course callback handler: {e}")
            await callback_query.answer("❌ Произошла ошибка при выборе курса")

    async def handle_message(self, message: Message):
        """Обработчик текстовых сообщений"""
        if message.text.startswith('/'):
            return

        user_id = message.from_user.id
        user_state = self.user_states.get(user_id)

        if not user_state or 'selected_course' not in user_state:
            return

        try:
            course_id = user_state['selected_course']
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await message.answer("❌ Курс не найден")
                    return

                # Здесь будет логика обработки вопроса через ИИ
                response = f"Это тестовый ответ на ваш вопрос:\n'{message.text}'\n\nПо курсу: *{course.title}*"
                await message.answer(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.answer("❌ Произошла ошибка при обработке вашего вопроса")

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Setting up bot commands...")
            await self.setup_bot_commands()

            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise