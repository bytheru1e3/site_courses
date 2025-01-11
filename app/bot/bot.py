import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, db, User
from flask import Flask
import requests
from app.services.ai_processor import AIProcessor

logger = logging.getLogger(__name__)

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

    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        try:
            self.dp.message.register(self.start_handler, Command("start"))
            self.dp.message.register(self.help_handler, Command("help"))
            self.dp.message.register(self.ask_handler, Command("ask"))
            self.dp.message.register(self.process_question)
            self.dp.callback_query.register(
                self.ask_course_callback_handler,
                lambda c: c.data.startswith('ask_course_')
            )
            self.dp.callback_query.register(
                self.after_question_callback_handler,
                lambda c: c.data in ['ask_new_question', 'end_dialog']
            )
        except Exception as e:
            logger.error(f"Error registering handlers: {e}", exc_info=True)

    async def start_handler(self, message: types.Message):
        """Обработчик команды /start"""
        try:
            welcome_text = (
                "👋 Добро пожаловать в ассистента по курсам!\n\n"
                "Доступные команды:\n"
                "/ask - Задать вопрос по материалам курса\n"
                "/help - Помощь и информация"
            )
            await message.answer(welcome_text)
        except Exception as e:
            logger.error(f"Error in start handler: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке команды")

    async def ask_handler(self, message: types.Message):
        """Показывает список курсов для выбора"""
        try:
            with self.app.app_context():
                courses = Course.query.all()
                if not courses:
                    await message.answer("📚 На данный момент нет доступных курсов")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"ask_course_{course.id}"
                    )]
                    for course in courses
                ])

                await message.answer(
                    "📚 Выберите курс, по которому хотите задать вопрос:",
                    reply_markup=keyboard
                )
                logger.info(f"Ask command processed for user {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error in ask handler: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при получении списка курсов")

    async def ask_course_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик выбора курса для вопроса"""
        try:
            course_id = int(callback.data.split('_')[2])
            user_id = callback.from_user.id

            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                # Сохраняем выбранный курс для пользователя
                self.user_states[user_id] = {
                    'waiting_for_question': True,
                    'course_id': course_id
                }

                await callback.message.edit_text(
                    f"📝 Вы выбрали курс: {course.title}\n\n"
                    "Теперь отправьте ваш вопрос в чат."
                )
                await callback.answer()

        except Exception as e:
            logger.error(f"Error in ask course callback handler: {e}")
            await callback.answer("❌ Произошла ошибка при выборе курса")

    async def process_question(self, message: types.Message):
        """Обработчик вопросов после выбора курса"""
        try:
            user_id = message.from_user.id
            user_state = self.user_states.get(user_id)

            if not user_state or not user_state.get('waiting_for_question'):
                return

            course_id = user_state['course_id']
            question = message.text

            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await message.reply("❌ Курс не найден")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Задать новый вопрос", callback_data="ask_new_question")],
                    [InlineKeyboardButton(text="✅ Завершить", callback_data="end_dialog")]
                ])

                await message.reply("🔍 Ищу ответ на ваш вопрос...")

                # Используем AIProcessor для получения ответа
                ai_processor = AIProcessor.get_instance()
                response = ai_processor.answer_question(question, course_id)

                if not response:
                    await message.reply(
                        "К сожалению, я не нашел релевантной информации по вашему вопросу.\n"
                        "Попробуйте переформулировать вопрос или выбрать другой курс.",
                        reply_markup=keyboard
                    )
                    return

                formatted_response = (
                    f"📚 Ответ по курсу «{course.title}»\n"
                    f"❓ Ваш вопрос: {question}\n\n"
                    f"🔍 {response}\n"
                )

                await message.reply(formatted_response, reply_markup=keyboard)
                logger.info(f"Answered question for user {message.from_user.id} about course {course_id}")

                # Очищаем состояние пользователя
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
                    "✅ Диалог завершен. Используйте /ask, чтобы задать новый вопрос."
                )

            await callback.answer()

        except Exception as e:
            logger.error(f"Error in after question callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def help_handler(self, message: types.Message):
        """Обработчик команды /help"""
        try:
            help_text = (
                "🔍 Справка по использованию бота:\n\n"
                "1️⃣ /start - Начать работу с ботом\n"
                "2️⃣ /ask - Задать вопрос по материалам курса\n"
                "3️⃣ /help - Показать это сообщение\n\n"
                "Как задать вопрос:\n"
                "1. Используйте команду /ask\n"
                "2. Выберите курс из списка\n"
                "3. Введите ваш вопрос\n"
                "4. Получите ответ с релевантной информацией\n"
                "5. Используйте кнопки для продолжения диалога"
            )
            await message.reply(help_text)
        except Exception as e:
            logger.error(f"Error in help handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке команды")

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")