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

    # Создаем экземпляр приложения
    app = create_app()

    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask application on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=True)
except Exception as e:
    logger.error(f"Failed to start application: {str(e)}", exc_info=True)
    raise