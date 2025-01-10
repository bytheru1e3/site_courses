import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, db, User
from flask import Flask
import requests
from app.services.file_processor import FileProcessor
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

API_BASE_URL = "http://127.0.0.1:5000/api/telegram"  # Адрес вашего Flask API

class CourseBot:
    def __init__(self, app: Flask):
        if not app:
            raise ValueError("Flask application must be provided")

        self.app = app
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

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
            self.dp.message.register(self.ask_handler, Command("ask"))  # Новый обработчик для вопросов
            self.dp.callback_query.register(
                self.course_callback_handler,
                lambda c: c.data.startswith('course_')
            )
            self.dp.callback_query.register(
                self.materials_callback_handler,
                lambda c: c.data.startswith('materials_')
            )
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
                "/ask - Задать вопрос по материалам курса\n"
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
                "telegram_id": message.from_user.id,
                "username": message.from_user.username or message.from_user.first_name,
                "email": email
            }
            response = requests.post(f"{API_BASE_URL}/register", json=data).json()

            if response.get("success"):
                await message.reply("✅ Регистрация прошла успешно!")
            else:
                await message.reply(f"❌ Ошибка регистрации: {response.get('error')}")

        except Exception as e:
            logger.error(f"Error in register handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при регистрации")

    async def auth_handler(self, message: types.Message):
        """Аутентификация пользователя через API"""
        try:
            logger.info(f"Auth command received from user {message.from_user.id}")
            data = {"telegram_id": message.from_user.id}
            response = requests.post(f"{API_BASE_URL}/auth", json=data).json()

            if response.get("success"):
                user = response.get("user")
                await message.reply(f"✅ Вы вошли как {user['username']} ({user['email']})")
            else:
                await message.reply(f"❌ Ошибка входа: {response.get('error')}")

        except Exception as e:
            logger.error(f"Error in auth handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при входе в систему")

    async def help_handler(self, message: types.Message):
        """Обработчик команды /help"""
        try:
            help_text = (
                "🔍 Справка по использованию бота:\n\n"
                "1️⃣ /start - Начать работу с ботом\n"
                "2️⃣ /register <email> - Зарегистрироваться\n"
                "3️⃣ /auth - Войти в систему\n"
                "4️⃣ /courses - Показать список доступных курсов\n"
                "5️⃣ /ask <id_курса> <вопрос> - Задать вопрос по материалам курса\n"
                "6️⃣ /help - Показать это сообщение\n\n"
                "После выбора курса вы сможете:\n"
                "📚 Просматривать материалы курса\n"
                "📝 Получать информацию о материалах\n"
                "❓ Задавать вопросы по материалам"
            )
            await message.reply(help_text)
        except Exception as e:
            logger.error(f"Error in help handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке команды")

    async def list_courses_handler(self, message: types.Message):
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

    async def course_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик выбора курса"""
        try:
            course_id = int(callback.data.split('_')[1])
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                text = f"📘 {course.title}\n\n{course.description or 'Описание отсутствует'}"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📚 Материалы курса",
                        callback_data=f"materials_{course_id}"
                    )]
                ])

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
        except Exception as e:
            logger.error(f"Error in course callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def materials_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик просмотра материалов курса"""
        try:
            course_id = int(callback.data.split('_')[1])
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                materials = course.materials
                if not materials:
                    await callback.message.edit_text("В этом курсе пока нет материалов")
                    await callback.answer()
                    return

                text = f"📚 Материалы курса {course.title}:\n\n"
                for material in materials:
                    text += f"📝 {material.title}\n"
                    if material.files:
                        for file in material.files:
                            text += f"📎 {file.filename}\n"
                    text += "\n"

                await callback.message.edit_text(text)
                await callback.answer()
        except Exception as e:
            logger.error(f"Error in materials callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def ask_handler(self, message: types.Message):
        """Обработчик команды /ask для вопросов по материалам"""
        try:
            # Проверяем формат команды
            command_parts = message.text.split(maxsplit=2)
            if len(command_parts) < 3:
                await message.reply(
                    "Для поиска используйте формат:\n"
                    "/ask <id_курса> <ваш_вопрос>\n"
                    "Например: /ask 1 Что такое векторная база данных?"
                )
                return

            # Получаем ID курса и вопрос
            try:
                course_id = int(command_parts[1])
            except ValueError:
                await message.reply("ID курса должен быть числом")
                return

            question = command_parts[2]

            with self.app.app_context():
                # Проверяем существование курса
                course = Course.query.get(course_id)
                if not course:
                    await message.reply("❌ Курс не найден")
                    return

                # Проверяем доступ пользователя к курсу
                user = User.query.filter_by(telegram_id=str(message.from_user.id)).first()
                if not user or not user.has_access_to_course(course):
                    await message.reply("❌ У вас нет доступа к этому курсу")
                    return

                # Поиск релевантных материалов
                await message.reply("🔍 Ищу ответ на ваш вопрос...")
                search_results = FileProcessor.search_similar_documents(question, top_k=3)

                if not search_results:
                    await message.reply("К сожалению, я не нашел релевантной информации по вашему вопросу")
                    return

                # Формируем ответ
                response = "📚 Вот что я нашел по вашему вопросу:\n\n"
                for idx, result in enumerate(search_results, 1):
                    response += f"{idx}. {result.get('text', 'Текст отсутствует')}\n\n"

                await message.reply(response)
                logger.info(f"Answered question for user {message.from_user.id} about course {course_id}")

        except Exception as e:
            logger.error(f"Error in ask handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке вашего вопроса")

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise