import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.models import Course, Material
from flask import Flask

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self, app: Flask):
        """Инициализация бота"""
        self.app = app  # Сохраняем ссылку на Flask приложение
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

        # Инициализация бота
        self.bot = Bot(token=self.token, parse_mode=ParseMode.HTML)
        self.dp = Dispatcher()

        # Словарь для хранения состояний пользователей
        self.user_states = {}

        # Регистрация обработчиков
        self.register_handlers()
        logger.info("Bot initialized successfully")

    async def setup_commands(self):
        """Настройка команд бота"""
        commands = [
            BotCommand(command="start", description="🚀 Начать работу"),
            BotCommand(command="help", description="ℹ️ Помощь"),
            BotCommand(command="courses", description="📚 Список курсов"),
            BotCommand(command="chat", description="💬 Задать вопрос")
        ]
        await self.bot.set_my_commands(commands)
        logger.info("Bot commands menu has been set up")

    def register_handlers(self):
        """Регистрация обработчиков команд"""
        # Основные команды
        self.dp.message.register(self.start_handler, CommandStart())
        self.dp.message.register(self.help_handler, Command(commands=["help"]))
        self.dp.message.register(self.list_courses_handler, Command(commands=["courses"]))
        self.dp.message.register(self.chat_handler, Command(commands=["chat"]))

        # Обработчики callback-запросов
        self.dp.callback_query.register(self.course_selected_handler, lambda c: c.data.startswith('course_'))
        self.dp.callback_query.register(self.chat_course_selected_handler, lambda c: c.data.startswith('chat_course_'))

        # Обработчик текстовых сообщений
        self.dp.message.register(self.handle_message)
        logger.info("Handlers registered successfully")

    async def start_handler(self, message: Message):
        """Обработчик команды /start"""
        try:
            welcome_text = (
                "👋 Добро пожаловать в бот системы управления курсами!\n\n"
                "Доступные команды:\n"
                "/courses - 📚 Просмотр списка курсов\n"
                "/chat - 💬 Задать вопрос\n"
                "/help - ℹ️ Помощь и информация"
            )
            await message.answer(welcome_text)
            logger.info(f"Start command processed for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await message.answer("❌ Произошла ошибка")

    async def help_handler(self, message: Message):
        """Обработчик команды /help"""
        try:
            help_text = (
                "🔍 Справка по использованию бота:\n\n"
                "1️⃣ /start - Начать работу с ботом\n"
                "2️⃣ /courses - Просмотр доступных курсов\n"
                "3️⃣ /chat - Задать вопрос по курсу\n"
                "4️⃣ /help - Показать это сообщение\n\n"
                "После выбора курса вы можете:\n"
                "📚 Просматривать материалы курса\n"
                "💬 Задавать вопросы по материалам"
            )
            await message.answer(help_text)
            logger.info(f"Help command processed for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error in help handler: {e}")
            await message.answer("❌ Произошла ошибка")

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

                await message.answer("📚 Доступные курсы:", reply_markup=keyboard)
                logger.info(f"Courses listed for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error in list courses handler: {e}")
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

                await message.answer("Выберите курс, по которому хотите задать вопрос:", reply_markup=keyboard)
                logger.info(f"Chat started for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            await message.answer("❌ Произошла ошибка при запуске чата")

    async def course_selected_handler(self, callback: CallbackQuery):
        """Обработчик выбора курса"""
        try:
            course_id = int(callback.data.split('_')[1])
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                await callback.message.edit_text(
                    f"📘 <b>{course.title}</b>\n\n"
                    f"{course.description or 'Описание отсутствует'}\n\n"
                    "Используйте команду /chat чтобы задать вопрос по этому курсу."
                )
                await callback.answer()
        except Exception as e:
            logger.error(f"Error in course selected handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def chat_course_selected_handler(self, callback: CallbackQuery):
        """Обработчик выбора курса для чата"""
        try:
            course_id = int(callback.data.split('_')[2])
            user_id = callback.from_user.id

            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                self.user_states[user_id] = {'course_id': course_id}

                await callback.message.edit_text(
                    f"Выбран курс: <b>{course.title}</b>\n"
                    "Теперь вы можете задать свой вопрос. Напишите его в чат."
                )
                await callback.answer()
        except Exception as e:
            logger.error(f"Error in chat course selected handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def handle_message(self, message: Message):
        """Обработчик текстовых сообщений"""
        if message.text.startswith('/'):
            return

        user_id = message.from_user.id
        user_state = self.user_states.get(user_id)

        if not user_state or 'course_id' not in user_state:
            await message.answer("Пожалуйста, сначала выберите курс с помощью команды /chat")
            return

        try:
            with self.app.app_context():
                course = Course.query.get(user_state['course_id'])
                if not course:
                    await message.answer("❌ Курс не найден")
                    return

                # Здесь будет логика обработки вопроса через ИИ
                response = (
                    f"Получен вопрос по курсу <b>{course.title}</b>:\n\n"
                    f"Ваш вопрос: {message.text}\n\n"
                    "Это тестовый ответ. В будущем здесь будет ответ от ИИ."
                )
                await message.answer(response)
                logger.info(f"Question processed for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.answer("❌ Произошла ошибка при обработке вопроса")

    async def start_polling(self):
        """Запуск бота"""
        try:
            await self.setup_commands()
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise