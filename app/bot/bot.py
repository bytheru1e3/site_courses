import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, db, User
from flask import Flask
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG level for more detailed logs

# Получаем домен Replit из переменных окружения
REPLIT_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN', '')
if not REPLIT_DOMAIN:
    logger.warning("REPLIT_DEV_DOMAIN not found in environment variables")
    API_BASE_URL = 'http://0.0.0.0:5000/api/telegram'
else:
    API_BASE_URL = f'https://{REPLIT_DOMAIN}/api/telegram'

logger.info(f"Using API URL: {API_BASE_URL}")

class CourseBot:
    def __init__(self, app: Flask):
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
            self.dp.message.register(self.start_handler, Command("start"))
            self.dp.message.register(self.register_handler, Command("register"))
            self.dp.message.register(self.auth_handler, Command("auth"))
            self.dp.message.register(self.list_courses_handler, Command("courses"))
            self.dp.message.register(self.help_handler, Command("help"))
            self.dp.message.register(self.chat_handler, Command("chat"))
            self.dp.callback_query.register(
                self.course_callback_handler,
                lambda c: c.data.startswith('course_')
            )
            self.dp.callback_query.register(
                self.materials_callback_handler,
                lambda c: c.data.startswith('materials_')
            )
            self.dp.callback_query.register(
                self.chat_course_callback_handler,
                lambda c: c.data.startswith('chat_course_')
            )
            # Обработчик всех текстовых сообщений
            self.dp.message.register(self.handle_message)
        except Exception as e:
            logger.error(f"Error registering handlers: {e}", exc_info=True)
            raise

    async def start_handler(self, message: types.Message):
        """Обработчик команды /start"""
        try:
            logger.info(f"Start command received from user {message.from_user.id}")
            welcome_text = (
                "👋 Добро пожаловать в бот системы управления курсами!\n\n"
                "Доступные команды:\n"
                "/register - Зарегистрироваться\n"
                "/auth - Войти в систему\n"
                "/courses - Просмотр списка курсов\n"
                "/chat - Начать чат с ассистентом\n"
                "/help - Помощь и информация"
            )
            await self.bot.send_message(chat_id=message.chat.id, text=welcome_text)
        except Exception as e:
            logger.error(f"Error in start handler: {e}", exc_info=True)
            await self.bot.send_message(chat_id=message.chat.id, text="❌ Произошла ошибка при обработке команды")

    async def register_handler(self, message: types.Message):
        """Регистрация пользователя через API"""
        try:
            logger.info(f"Register command received from user {message.from_user.id}")
            if len(message.text.split()) < 2:
                await message.reply("Введите email для регистрации: /register <email>")
                return

            email = message.text.split(maxsplit=1)[1]
            data = {
                "telegram_id": str(message.from_user.id),  # Convert to string for JSON
                "username": message.from_user.username or message.from_user.first_name,
                "email": email
            }

            logger.info(f"Sending registration request to API: {API_BASE_URL}/register")
            try:
                response = requests.post(f"{API_BASE_URL}/register", json=data, timeout=10)
                response_data = response.json()

                if response_data.get("success"):
                    await message.reply("✅ Регистрация прошла успешно!")
                else:
                    error_msg = response_data.get('error', 'Неизвестная ошибка')
                    await message.reply(f"❌ Ошибка регистрации: {error_msg}")
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                await message.reply("❌ Ошибка подключения к серверу. Попробуйте позже.")

        except Exception as e:
            logger.error(f"Error in register handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при регистрации")

    async def auth_handler(self, message: types.Message):
        """Аутентификация пользователя через API"""
        try:
            logger.info(f"Auth command received from user {message.from_user.id}")
            data = {"telegram_id": str(message.from_user.id)}  # Convert to string for JSON

            logger.info(f"Sending auth request to API: {API_BASE_URL}/auth")
            try:
                response = requests.post(f"{API_BASE_URL}/auth", json=data, timeout=10)
                response_data = response.json()

                if response_data.get("success"):
                    user = response_data.get("user")
                    await message.reply(f"✅ Вы вошли как {user['username']} ({user['email']})")
                else:
                    error_msg = response_data.get('error', 'Неизвестная ошибка')
                    await message.reply(f"❌ Ошибка входа: {error_msg}")
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                await message.reply("❌ Ошибка подключения к серверу. Попробуйте позже.")

        except Exception as e:
            logger.error(f"Error in auth handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при входе в систему")

    async def chat_handler(self, message: types.Message):
        """Handler for /chat command"""
        try:
            logger.debug(f"Chat command received from user {message.from_user.id}")
            with self.app.app_context():
                courses = Course.query.all()
                logger.debug(f"Found {len(courses)} courses")

                if not courses:
                    await message.reply("📚 На данный момент нет доступных курсов.")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"chat_course_{course.id}"
                    )]
                    for course in courses
                ])

                await message.reply(
                    "Выберите курс, по которому хотите задать вопрос:",
                    reply_markup=keyboard
                )
                logger.debug(f"Sent course selection keyboard to user {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}", exc_info=True)
            await message.reply("❌ Произошла ошибка при запуске чата")

    async def chat_course_callback_handler(self, callback_query: types.CallbackQuery):
        """Handler for course selection in chat"""
        try:
            user_id = callback_query.from_user.id
            course_id = int(callback_query.data.split('_')[2])
            logger.debug(f"User {user_id} selected course {course_id} for chat")

            # Save selected course in user state
            self.user_states[user_id] = {'selected_course': course_id}

            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    logger.error(f"Course {course_id} not found")
                    await callback_query.answer("❌ Курс не найден")
                    return

                await self.bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=f"Вы выбрали курс: {course.title}\nТеперь вы можете задать свой вопрос, и я постараюсь на него ответить."
                )
                await callback_query.answer()
                logger.debug(f"Course {course_id} selected successfully for user {user_id}")

        except Exception as e:
            logger.error(f"Error in chat course callback handler: {str(e)}", exc_info=True)
            await callback_query.answer("❌ Произошла ошибка при выборе курса")

    async def handle_message(self, message: types.Message):
        """Handler for text messages"""
        try:
            # Skip commands
            if message.text.startswith('/'):
                return

            user_id = message.from_user.id
            user_state = self.user_states.get(user_id)
            logger.debug(f"Processing message from user {user_id}, state: {user_state}")

            # If user hasn't selected a course, ignore the message
            if not user_state or 'selected_course' not in user_state:
                logger.debug(f"User {user_id} has not selected a course yet")
                return

            course_id = user_state['selected_course']
            logger.debug(f"Processing question for course {course_id} from user {user_id}")

            # Here will be AI processing logic
            # For now, return a test response
            response = {
                'success': True,
                'answer': f"Это тестовый ответ на ваш вопрос: '{message.text}'\nПо курсу с ID: {course_id}"
            }

            await message.reply(response['answer'])
            logger.debug(f"Sent answer to user {user_id}")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке вашего вопроса")

    async def help_handler(self, message: types.Message):
        """Обработчик команды /help"""
        try:
            help_text = (
                "🔍 Справка по использованию бота:\n\n"
                "1️⃣ /start - Начать работу с ботом\n"
                "2️⃣ /register <email> - Зарегистрироваться\n"
                "3️⃣ /auth - Войти в систему\n"
                "4️⃣ /courses - Показать список доступных курсов\n"
                "5️⃣ /chat - Начать чат с ассистентом\n"
                "6️⃣ /help - Показать это сообщение\n\n"
                "После выбора курса вы сможете:\n"
                "📚 Просматривать материалы курса\n"
                "💬 Задавать вопросы по материалам\n"
                "📝 Получать информацию о материалах"
            )
            await message.reply(help_text)
        except Exception as e:
            logger.error(f"Error in help handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке команды")

    async def list_courses_handler(self, message: types.Message):
        """Обработчик команды /courses"""
        try:
            logger.info(f"Courses command received from user {message.from_user.id}")
            with self.app.app_context():
                courses = Course.query.all()
                logger.info(f"Found {len(courses)} courses")

                if not courses:
                    await self.bot.send_message(chat_id=message.chat.id, text="📚 На данный момент нет доступных курсов.")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"course_{course.id}"
                    )]
                    for course in courses
                ])

                await self.bot.send_message(
                    chat_id=message.chat.id,
                    text="📚 Список доступных курсов:",
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error in list_courses_handler: {e}", exc_info=True)
            await self.bot.send_message(chat_id=message.chat.id, text="❌ Произошла ошибка при получении списка курсов")

    async def course_callback_handler(self, callback_query: types.CallbackQuery):
        """Обработчик выбора курса"""
        try:
            logger.info(f"Course callback received from user {callback_query.from_user.id}")
            with self.app.app_context():
                course_id = int(callback_query.data.split('_')[1])
                course = Course.query.get(course_id)

                if not course:
                    logger.warning(f"Course {course_id} not found")
                    await callback_query.answer("❌ Курс не найден")
                    return

                course_info = (
                    f"📘 *{course.title}*\n"
                    f"📝 {course.description or 'Описание отсутствует'}\n\n"
                )

                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="📚 Показать материалы",
                        callback_data=f"materials_{course_id}"
                    )
                ]])

                await self.bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=course_info,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                await callback_query.answer()

        except Exception as e:
            logger.error(f"Error in course_callback_handler: {e}", exc_info=True)
            await callback_query.answer("❌ Произошла ошибка при получении информации о курсе")

    async def materials_callback_handler(self, callback_query: types.CallbackQuery):
        """Обработчик просмотра материалов курса"""
        try:
            logger.info(f"Materials callback received from user {callback_query.from_user.id}")
            with self.app.app_context():
                course_id = int(callback_query.data.split('_')[1])
                course = Course.query.get(course_id)

                if not course:
                    logger.warning(f"Course {course_id} not found")
                    await callback_query.answer("❌ Курс не найден")
                    return

                materials = course.materials
                if not materials:
                    await self.bot.send_message(
                        chat_id=callback_query.message.chat.id,
                        text=f"📚 В курсе *{course.title}* пока нет материалов.",
                        parse_mode="Markdown"
                    )
                    await callback_query.answer()
                    return

                materials_text = f"📚 Материалы курса *{course.title}*:\n\n"
                for material in materials:
                    materials_text += (
                        f"📑 *{material.title}*\n"
                        f"└ {material.content[:100]}{'...' if len(material.content) > 100 else ''}\n\n"
                    )

                await self.bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=materials_text,
                    parse_mode="Markdown"
                )
                await callback_query.answer()

        except Exception as e:
            logger.error(f"Error in materials_callback_handler: {e}", exc_info=True)
            await callback_query.answer("❌ Произошла ошибка при получении материалов курса")

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}", exc_info=True)
            raise