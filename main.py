import os
from app import create_app

# Создаем директории для загрузки файлов и векторной БД
os.makedirs(os.path.join(os.getcwd(), 'app', 'uploads'), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), 'app', 'data'), exist_ok=True)

# Удаляем старые файлы индекса и документов
vector_index_path = os.path.join(os.getcwd(), 'app', 'data', 'vector_index.faiss')
documents_path = os.path.join(os.getcwd(), 'app', 'data', 'documents.json')

if os.path.exists(vector_index_path):
    os.remove(vector_index_path)
if os.path.exists(documents_path):
    os.remove(documents_path)

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)