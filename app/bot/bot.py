from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from app.models import Course, Material, ChatHistory
from app import db
from app.services.vector_search import VectorSearch
from app.config import Config
import logging

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self, token):
        self.application = ApplicationBuilder().token(token).build()
        self.vector_search = VectorSearch()
        self.setup_handlers()
        logger.info("Bot initialized with handlers")

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("courses", self.list_courses))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        logger.info("Handlers setup completed")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        logger.info(f"Received /start command from chat {update.effective_chat.id}")
        welcome_text = """
        👋 Привет! Я бот поддержки курсов.

        🔍 Я могу:
        - Показать список доступных курсов
        - Ответить на вопросы по материалам

        Используйте /help для просмотра доступных команд.
        """
        await update.message.reply_text(welcome_text)
        logger.info(f"Sent welcome message to chat {update.effective_chat.id}")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        logger.info(f"Received /help command from chat {update.effective_chat.id}")
        help_text = """
        📚 Доступные команды:
        /start - Начать работу с ботом
        /help - Показать это сообщение
        /courses - Показать список доступных курсов

        ❓ Вы также можете задать мне вопрос по материалам курсов!
        """
        await update.message.reply_text(help_text)
        logger.info(f"Sent help message to chat {update.effective_chat.id}")

    async def list_courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /courses"""
        logger.info(f"Received /courses command from chat {update.effective_chat.id}")
        try:
            courses = Course.query.all()
            if not courses:
                await update.message.reply_text("📝 Пока нет доступных курсов")
                return

            courses_text = "📚 Доступные курсы:\n\n"
            for course in courses:
                courses_text += f"🔹 {course.title}\n"
                if course.description:
                    courses_text += f"└ {course.description}\n"
                courses_text += f"└ Материалов: {len(course.materials)}\n\n"

            await update.message.reply_text(courses_text)
            logger.info(f"Sent courses list to chat {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"Error listing courses: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении списка курсов"
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_message = update.message.text
        user_id = str(update.effective_user.id)
        logger.info(f"Received message from user {user_id}: {user_message}")

        try:
            # Поиск релевантных материалов
            search_results = self.vector_search.search(user_message)

            if not search_results:
                response = "❌ Извините, я не нашел подходящей информации по вашему вопросу"
            else:
                # Формируем ответ из найденных материалов
                best_match = search_results[0]
                response = f"📖 Вот что я нашел по вашему вопросу:\n\n{best_match['content']}"

            # Сохраняем историю чата
            chat_history = ChatHistory(
                telegram_user_id=user_id,
                message=user_message,
                response=response
            )
            db.session.add(chat_history)
            db.session.commit()

            await update.message.reply_text(response)
            logger.info(f"Processed message from user {user_id} and sent response")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "❌ Извините, произошла ошибка при обработке вашего сообщения"
            )

    async def run_polling(self):
        """Асинхронный запуск бота"""
        logger.info("Starting bot polling")
        await self.application.initialize()
        await self.application.start()
        await self.application.run_polling()
        logger.info("Bot polling started")