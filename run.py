import os
import logging
from app import create_app
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting application initialization...")

    # Проверяем наличие переменной окружения DATABASE_URL
    if not os.environ.get('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable is not set")
        raise ValueError("DATABASE_URL environment variable is not set")

    logger.info("Creating Flask application instance...")
    app = create_app()

    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask application on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=True)
except Exception as e:
    logger.error(f"Failed to start application: {str(e)}", exc_info=True)
    raise