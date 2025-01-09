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

    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    if not SQLALCHEMY_DATABASE_URI:
        logger.error("DATABASE_URL environment variable is not set")
        raise ValueError("DATABASE_URL environment variable is not set")
    else:
        logger.info(f"Using database: {SQLALCHEMY_DATABASE_URI.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URI else 'local'}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info(f"Upload folder created at: {UPLOAD_FOLDER}")

    # Vector Database settings
    VECTOR_DB_INDEX_FILE = os.path.join(os.getcwd(), 'app', 'data', 'vector_index.faiss')
    VECTOR_DB_DOCUMENTS_FILE = os.path.join(os.getcwd(), 'app', 'data', 'documents.json')
    os.makedirs(os.path.dirname(VECTOR_DB_INDEX_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(VECTOR_DB_DOCUMENTS_FILE), exist_ok=True)
    logger.info("Vector database directories created")

    EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    # File Processing
    ALLOWED_EXTENSIONS = {'docx', 'pdf'}
    logger.info("Configuration loaded successfully")