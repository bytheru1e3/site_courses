from app import create_app, db
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Создание таблиц базы данных
        try:
            db.create_all()
            logger.info("Database tables created successfully")

            # Создание администратора по умолчанию, если его нет
            from app.models import User
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                logger.info("Default admin user created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    # Запуск Flask приложения
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )