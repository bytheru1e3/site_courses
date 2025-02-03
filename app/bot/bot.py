# bot.py
import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .ai_processing import VectorDatabase

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self):
        self.token = '7884948980:AAFSmEjRYMvE-tgv82wWquqd2v0_L6C-Pd8'
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()
        self.user_states = {}
        self.vector_db = VectorDatabase()
        self._register_handlers()

    def _register_handlers(self):
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.help_handler, Command("help"))
        self.dp.message.register(self.list_courses_handler, Command("courses"))
        self.dp.message.register(self.ask_handler, Command("ask"))
        self.dp.message.register(self.process_question)
        self.dp.callback_query.register(self.course_callback_handler, lambda c: c.data.startswith('course_'))
        self.dp.callback_query.register(self.materials_callback_handler, lambda c: c.data.startswith('materials_'))
        self.dp.callback_query.register(self.ask_course_callback_handler, lambda c: c.data.startswith('ask_course_'))
        self.dp.callback_query.register(self.after_question_callback_handler, lambda c: c.data == 'end_dialog')

    # Исходные обработчики из предоставленного кода
    def _register_handlers(self):
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.help_handler, Command("help"))
        self.dp.message.register(self.list_courses_handler, Command("courses"))
        self.dp.message.register(self.ask_handler, Command("ask"))
        self.dp.message.register(self.process_question)
        self.dp.callback_query.register(self.course_callback_handler, lambda c: c.data.startswith('course_'))
        self.dp.callback_query.register(self.materials_callback_handler, lambda c: c.data.startswith('materials_'))
        self.dp.callback_query.register(self.ask_course_callback_handler, lambda c: c.data.startswith('ask_course_'))
        self.dp.callback_query.register(self.after_question_callback_handler, lambda c: c.data == 'end_dialog')

    async def start_handler(self, message: types.Message):
        welcome_text = (
            "👋 Добро пожаловать в бот системы управления курсами!\n\n"
            "Доступные команды:\n"
            "/register - Зарегистрироваться\n"
            "/auth - Войти в систему\n"
            "/courses - Просмотр списка курсов\n"
            "/ask - Задать вопрос по материалам курса\n"
            "/help - Помощь"
        )
        await message.answer(welcome_text)

    async def ask_handler(self, message: types.Message):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📘 Курс 1", callback_data="ask_course_1")]
        ])
        await message.answer("📚 Выберите курс:", reply_markup=keyboard)

    async def ask_course_callback_handler(self, callback: types.CallbackQuery):
        course_id = int(callback.data.split('_')[2])
        self.user_states[callback.from_user.id] = {
            'course_id': course_id,
            'in_dialog': True
        }
        await callback.message.edit_text(
            f"📝 Вы выбрали курс {course_id}. Отправьте ваш вопрос.\n\n"
            "Вы можете задавать вопросы один за другим. "
            "Для завершения нажмите кнопку ниже.",
            reply_markup=self._get_dialog_keyboard()
        )
        await callback.answer()

    async def process_question(self, message: types.Message):
        user_id = message.from_user.id
        if not self.user_states.get(user_id, {}).get('in_dialog'):
            return

        try:
            # Отправляем статус "Бот думает..."
            thinking_msg = await message.answer("⏳ Ищу ответ...")
            
            response = self.vector_db.generate_response(message.text)
            
            # Удаляем статус
            await self.bot.delete_message(
                chat_id=message.chat.id,
                message_id=thinking_msg.message_id
            )
            
            await message.answer(
                f"📚 Ответ:\n\n{response}",
                reply_markup=self._get_dialog_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await message.answer(
                "❌ Ошибка обработки запроса",
                reply_markup=self._get_dialog_keyboard()
            )
    
    def _get_dialog_keyboard(self):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Завершить диалог", callback_data="end_dialog")]
        ])

    async def after_question_callback_handler(self, callback: types.CallbackQuery):
        user_id = callback.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
        
        await callback.message.edit_text(
            "✅ Диалог завершен. Используйте /ask для нового вопроса.",
            reply_markup=None
        )
        await callback.answer()

    async def list_courses_handler(self, message: types.Message):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📘 Курс 1", callback_data="course_1")]
        ])
        await message.answer("📚 Доступные курсы:", reply_markup=keyboard)

    async def course_callback_handler(self, callback: types.CallbackQuery):
        course_id = int(callback.data.split('_')[1])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Материалы", callback_data=f"materials_{course_id}")]
        ])
        await callback.message.edit_text(f"📘 Курс {course_id}", reply_markup=keyboard)
        await callback.answer()

    async def materials_callback_handler(self, callback: types.CallbackQuery):
        course_id = int(callback.data.split('_')[1])
        await callback.message.edit_text(f"📚 Материалы курса {course_id}:\n\n1. Лекция 1\n2. Практика 1")
        await callback.answer()

    async def after_question_callback_handler(self, callback: types.CallbackQuery):
        await callback.message.edit_text("✅ Диалог завершен")
        await callback.answer()

    async def help_handler(self, message: types.Message):
        help_text = (
            "🔍 Справка:\n"
            "/start - Главное меню\n"
            "/courses - Список курсов\n"
            "/ask - Задать вопрос\n"
            "/help - Эта справка"
        )
        await message.answer(help_text)

    async def start_polling(self):
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    bot = CourseBot()
    asyncio.run(bot.start_polling())