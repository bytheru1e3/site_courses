import os
import secrets
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'docx', 'pdf'}

    def __init__(self):
        if not self.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable is not set")
        logger.info(f"Database URL configured: {self.SQLALCHEMY_DATABASE_URI.split('@')[1] if self.SQLALCHEMY_DATABASE_URI else 'Not set'}")

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Create required directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Upload folder created at: {Config.UPLOAD_FOLDER}")