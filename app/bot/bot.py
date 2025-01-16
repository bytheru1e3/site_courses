import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, db, User
from flask import Flask
import requests
from app.services.vector_db import VectorDB
from app.ai import answer_question

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
        self.user_states = {}
        self._register_handlers()
        logger.info("Bot handlers registered successfully")

        # Инициализация VectorDB
        self.vector_db_path = os.path.join(os.getcwd(), "app", "data")
        logger.info(f"Vector DB path: {self.vector_db_path}")

    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        try:
            self.dp.message.register(self.start_handler, Command("start"))
            self.dp.message.register(self.register_handler, Command("register"))
            self.dp.message.register(self.auth_handler, Command("auth"))
            self.dp.message.register(self.list_courses_handler, Command("courses"))
            self.dp.message.register(self.help_handler, Command("help"))
            self.dp.message.register(self.process_question)  # Обработчик для вопросов после выбора курса
            self.dp.callback_query.register(
                self.course_callback_handler,
                lambda c: c.data.startswith('course_')
            )
            self.dp.callback_query.register(
                self.materials_callback_handler,
                lambda c: c.data.startswith('materials_')
            )
            self.dp.callback_query.register(
                self.after_question_callback_handler,
                lambda c: c.data in ['ask_new_question', 'end_dialog']
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
                "/courses - Просмотр списка курсов\n"
                "/help - Помощь и информация"
            )
            await self.bot.send_message(chat_id=message.chat.id, text=welcome_text)
        except Exception as e:
            logger.error(f"Error in start handler: {e}", exc_info=True)
            await self.bot.send_message(chat_id=message.chat.id, text="❌ Произошла ошибка при обработке команды")

    async def help_handler(self, message: types.Message):
        """Обработчик команды /help"""
        try:
            help_text = (
                "🔍 Справка по использованию бота:\n\n"
                "1️⃣ /start - Начать работу с ботом\n"
                "2️⃣ /courses - Показать список доступных курсов\n"
                "3️⃣ /help - Показать это сообщение\n\n"
                "Как задать вопрос:\n"
                "1. Используйте команду /courses\n"
                "2. Выберите курс из списка\n"
                "3. Задайте свой вопрос\n"
                "4. Получите ответ с релевантной информацией"
            )
            await message.reply(help_text)
        except Exception as e:
            logger.error(f"Error in help handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке команды")

    async def process_question(self, message: types.Message):
        """Обработчик вопросов после выбора курса"""
        try:
            user_id = message.from_user.id
            user_state = self.user_states.get(user_id)

            # Проверяем, ожидаем ли мы вопрос от этого пользователя
            if not user_state or not user_state.get('waiting_for_question'):
                return

            course_id = user_state['course_id']
            question = message.text

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

                # Поиск ответа с использованием векторной базы данных
                await message.reply("🔍 Ищу ответ на ваш вопрос...")

                try:
                    answer = answer_question(question, self.vector_db_path)

                    # Создаем клавиатуру с кнопками
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📝 Задать новый вопрос", callback_data="ask_new_question")],
                        [InlineKeyboardButton(text="✅ Завершить", callback_data="end_dialog")]
                    ])

                    if not answer or "К сожалению, я не нашел информации" in answer:
                        await message.reply(
                            "❌ К сожалению, я не нашел релевантной информации по вашему вопросу.\n"
                            "💡 Попробуйте переформулировать вопрос или выбрать другой курс.",
                            reply_markup=keyboard
                        )
                        return

                    # Формируем полный ответ с улучшенным форматированием
                    full_response = (
                        f"📚 <b>Результаты поиска по курсу</b>\n"
                        f"<i>{course.title}</i>\n\n"
                        f"❓ <b>Ваш вопрос:</b>\n{question}\n\n"
                        f"🔍 <b>Найденная информация:</b>\n{answer}"
                    )

                    # Отправляем ответ с разбиением на части при необходимости
                    await self.send_split_message(
                        chat_id=message.chat.id,
                        text=full_response,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    logger.info(f"Answered question for user {message.from_user.id} about course {course_id}")

                except Exception as e:
                    logger.error(f"Error processing question: {str(e)}", exc_info=True)
                    await message.reply(
                        "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз.",
                        reply_markup=keyboard
                    )

                # Очищаем состояние пользователя после обработки вопроса
                self.user_states.pop(user_id, None)

        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке вашего вопроса")
            if user_id in locals():
                self.user_states.pop(user_id, None)

    async def after_question_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик действий после получения ответа на вопрос"""
        try:
            action = callback.data

            if action == "ask_new_question":
                # Показываем список курсов для нового вопроса
                with self.app.app_context():
                    courses = Course.query.all()
                    if not courses:
                        await callback.message.edit_text("📚 На данный момент нет доступных курсов")
                        return

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"📘 {course.title}",
                            callback_data=f"ask_course_{course.id}"
                        )]
                        for course in courses
                    ])

                    await callback.message.edit_text(
                        "📚 Выберите курс, по которому хотите задать вопрос:",
                        reply_markup=keyboard
                    )

            elif action == "end_dialog":
                await callback.message.edit_text(
                    "✅ Диалог завершен. Используйте /courses, чтобы задать новый вопрос."
                )

            await callback.answer()

        except Exception as e:
            logger.error(f"Error in after question callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def register_handler(self, message: types.Message):
        """Регистрация пользователя через API"""
        try:
            logger.info(f"Register command received from user {message.from_user.id}")
            if len(message.text.split()) < 2:
                await message.reply(
                    "Введите email для регистрации: /register <email>\n"
                    "Например: /register user@example.com"
                )
                return

            email = message.text.split(maxsplit=1)[1]
            data = {
                "telegram_id": message.from_user.id,
                "username": message.from_user.username or message.from_user.first_name,
                "email": email
            }
            response = requests.post(f"{API_BASE_URL}/register", json=data).json()

            if response.get("success"):
                await message.reply(
                    "✅ Регистрация прошла успешно!\n"
                    "Теперь вы можете использовать команду /courses для поиска информации в материалах курсов."
                )
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
                await message.reply(
                    f"✅ Вы вошли как {user['username']} ({user['email']})\n"
                    "Используйте /courses для поиска информации в материалах курсов."
                )
            else:
                await message.reply(
                    f"❌ Ошибка входа: {response.get('error')}\n"
                    "Используйте /register для регистрации."
                )

        except Exception as e:
            logger.error(f"Error in auth handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при входе в систему")

    async def list_courses_handler(self, message: types.Message):
        """Обработчик команды /courses"""
        try:
            with self.app.app_context():
                # Проверяем авторизацию пользователя
                user = User.query.filter_by(telegram_id=str(message.from_user.id)).first()
                if not user:
                    await message.answer(
                        "❌ Пожалуйста, сначала зарегистрируйтесь с помощью команды /register <email>"
                    )
                    return

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

                await message.answer(
                    "📚 Выберите курс для поиска информации или задания вопроса:",
                    reply_markup=keyboard
                )
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

                # Сохраняем выбранный курс для пользователя
                user_id = callback.from_user.id
                self.user_states[user_id] = {
                    'waiting_for_question': True,
                    'course_id': course_id
                }

                text = (
                    f"📘 Курс: {course.title}\n\n"
                    f"{course.description or 'Описание отсутствует'}\n\n"
                    "✍️ Теперь вы можете задать вопрос по материалам этого курса.\n"
                    "Просто отправьте ваш вопрос в следующем сообщении."
                )

                await callback.message.edit_text(text)
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

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def send_split_message(self, chat_id: int, text: str, parse_mode=None, reply_markup=None):
        """Отправка длинного сообщения с разбиением на части"""
        MAX_MESSAGE_LENGTH = 3000  # Maximum length for a single message

        try:
            if len(text) <= MAX_MESSAGE_LENGTH:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                return

            parts = []
            while text:
                if len(text) <= MAX_MESSAGE_LENGTH:
                    parts.append(text)
                    break

                # Find the best split point
                split_point = text[:MAX_MESSAGE_LENGTH].rfind('</b>')
                if split_point == -1:
                    split_point = text[:MAX_MESSAGE_LENGTH].rfind('</i>')
                if split_point == -1:
                    split_point = text[:MAX_MESSAGE_LENGTH].rfind('\n')
                if split_point == -1:
                    split_point = text[:MAX_MESSAGE_LENGTH].rfind('. ')
                if split_point == -1:
                    split_point = text[:MAX_MESSAGE_LENGTH].rfind(' ')
                if split_point == -1:
                    split_point = MAX_MESSAGE_LENGTH

                # Add part and prepare for next iteration
                part = text[:split_point]

                # Handle HTML tags
                if parse_mode == "HTML":
                    # Count open tags
                    open_b = part.count('<b>') - part.count('</b>')
                    open_i = part.count('<i>') - part.count('</i>')

                    # Close open tags
                    if open_b > 0:
                        part += '</b>' * open_b
                    if open_i > 0:
                        part += '</i>' * open_i

                parts.append(part)

                # Prepare next part
                text = text[split_point:].lstrip()

                # Restore HTML tags for next part
                if parse_mode == "HTML":
                    if open_b > 0:
                        text = '<b>' * open_b + text
                    if open_i > 0:
                        text = '<i>' * open_i + text

            # Send message parts
            total_parts = len(parts)
            for i, part in enumerate(parts):
                try:
                    # Add part indicator
                    if total_parts > 1:
                        if parse_mode == "HTML":
                            part += f"\n\n<i>📄 Часть {i+1} из {total_parts}</i>"
                        else:
                            part += f"\n\n📄 Часть {i+1} из {total_parts}"

                    # Send with appropriate markup
                    if i == total_parts - 1:  # Last part
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode=parse_mode,
                            reply_markup=reply_markup
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode=parse_mode
                        )

                    # Add small delay between messages
                    if i < total_parts - 1:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error sending message part {i+1}: {str(e)}")
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Ошибка при отправке части {i+1} сообщения",
                        parse_mode=None
                    )

        except Exception as e:
            logger.error(f"Error in send_split_message: {str(e)}")
            await self.bot.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при отправке сообщения"
            )