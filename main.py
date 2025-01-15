from flask import Flask
from app import db
import os

# Создаем экземпляр приложения
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev')

# Инициализируем расширения
db.init_app(app)

# Создаем директории для загрузки файлов и векторной БД
os.makedirs(os.path.join(os.getcwd(), 'app', 'uploads'), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), 'app', 'data'), exist_ok=True)

# Регистрируем маршруты
from app.routes import main
app.register_blueprint(main)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)