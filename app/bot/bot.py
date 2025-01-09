import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, Material, db

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self):
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

        logger.info("Initializing Telegram bot...")
        self.bot = Bot(token=token)
        self.dp = Dispatcher()

        # Регистрация обработчиков
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.list_courses_handler, Command("courses"))
        self.dp.message.register(self.help_handler, Command("help"))
        self.dp.callback_query.register(self.course_callback_handler, lambda c: c.data.startswith('course_'))
        self.dp.callback_query.register(self.materials_callback_handler, lambda c: c.data.startswith('materials_'))
        logger.info("Bot handlers registered successfully")

    async def start_handler(self, message: types.Message):
        """Обработчик команды /start"""
        logger.info(f"Start command received from user {message.from_user.id}")
        welcome_text = (
            "👋 Добро пожаловать в бот системы управления курсами!\n\n"
            "Доступные команды:\n"
            "/courses - Просмотр списка курсов\n"
            "/help - Помощь и информация"
        )
        await message.answer(welcome_text)

    async def help_handler(self, message: types.Message):
        """Обработчик команды /help"""
        logger.info(f"Help command received from user {message.from_user.id}")
        help_text = (
            "🔍 Справка по использованию бота:\n\n"
            "1️⃣ /start - Начать работу с ботом\n"
            "2️⃣ /courses - Показать список доступных курсов\n"
            "3️⃣ /help - Показать это сообщение\n\n"
            "После выбора курса вы сможете:\n"
            "📚 Просматривать материалы курса\n"
            "📝 Получать информацию о материалах"
        )
        await message.answer(help_text)

    async def list_courses_handler(self, message: types.Message):
        """Обработчик команды /courses"""
        logger.info(f"Courses command received from user {message.from_user.id}")
        try:
            # Проверяем подключение к базе данных
            if not db.engine.dialect.has_table(db.engine, 'courses'):
                logger.error("Courses table not found in database")
                await message.answer("❌ Ошибка доступа к базе данных")
                return

            courses = Course.query.all()
            logger.info(f"Found {len(courses)} courses")

            if not courses:
                await message.answer("📚 На данный момент нет доступных курсов.")
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
            logger.error(f"Error in list_courses_handler: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка при получении списка курсов.")

    async def course_callback_handler(self, callback_query: types.CallbackQuery):
        """Обработчик выбора курса"""
        logger.info(f"Course callback received from user {callback_query.from_user.id}")
        try:
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

            await callback_query.message.answer(
                course_info,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            await callback_query.answer()

        except Exception as e:
            logger.error(f"Error in course_callback_handler: {str(e)}", exc_info=True)
            await callback_query.answer("❌ Произошла ошибка при получении информации о курсе")

    async def materials_callback_handler(self, callback_query: types.CallbackQuery):
        """Обработчик просмотра материалов курса"""
        logger.info(f"Materials callback received from user {callback_query.from_user.id}")
        try:
            course_id = int(callback_query.data.split('_')[1])
            course = Course.query.get(course_id)

            if not course:
                logger.warning(f"Course {course_id} not found")
                await callback_query.answer("❌ Курс не найден")
                return

            materials = course.materials
            if not materials:
                await callback_query.message.answer(
                    f"📚 В курсе *{course.title}* пока нет материалов.",
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

            await callback_query.message.answer(
                materials_text,
                parse_mode="Markdown"
            )
            await callback_query.answer()

        except Exception as e:
            logger.error(f"Error in materials_callback_handler: {str(e)}", exc_info=True)
            await callback_query.answer("❌ Произошла ошибка при получении материалов курса")

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}", exc_info=True)
            raise

course_bot = CourseBot()