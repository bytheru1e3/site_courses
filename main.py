import os
from app import create_app

# Создаем директории для загрузки файлов и векторной БД
os.makedirs(os.path.join(os.getcwd(), 'app', 'uploads'), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), 'app', 'data'), exist_ok=True)

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
