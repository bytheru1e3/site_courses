from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from app.models import Course, Material, ChatHistory
from app import db
from app.services.vector_search import VectorSearch
import logging

logger = logging.getLogger(__name__)

class CourseBot:
    def __init__(self, token):
        self.application = ApplicationBuilder().token(token).build()
        self.vector_search = VectorSearch()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("courses", self.list_courses))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Привет! Я бот поддержки курсов. Используйте /help для просмотра доступных команд."
        )
        logger.info(f"User {update.effective_user.id} started the bot")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
        Доступные команды:
        /start - Начать работу с ботом
        /help - Показать это сообщение
        /courses - Показать доступные курсы
        
        Вы также можете задать мне вопрос по материалам курсов!
        """
        await update.message.reply_text(help_text)

    async def list_courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            courses = Course.query.all()
            if not courses:
                await update.message.reply_text("Пока нет доступных курсов")
                return

            course_list = "\n".join([f"📚 {course.title}\n{course.description}\n" 
                                   for course in courses])
            await update.message.reply_text(f"Доступные курсы:\n\n{course_list}")
        except Exception as e:
            logger.error(f"Error listing courses: {e}")
            await update.message.reply_text("Произошла ошибка при получении списка курсов")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        user_id = str(update.effective_user.id)

        try:
            # Поиск релевантных материалов
            search_results = self.vector_search.search(user_message)
            
            if not search_results:
                response = "Извините, я не нашел подходящей информации по вашему вопросу"
            else:
                # Формируем ответ из найденных материалов
                best_match = search_results[0]
                response = f"Вот что я нашел по вашему вопросу:\n\n{best_match['content']}"

            # Сохраняем историю чата
            chat_history = ChatHistory(
                telegram_user_id=user_id,
                message=user_message,
                response=response
            )
            db.session.add(chat_history)
            db.session.commit()

            await update.message.reply_text(response)
            logger.info(f"Processed message from user {user_id}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке вашего сообщения"
            )

    def run(self):
        self.application.run_polling()
        logger.info("Bot started polling")
