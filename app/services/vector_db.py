import os
import json
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(
        self,
        index_file="app/data/vector_index.faiss",
        documents_file="app/data/documents.json"
    ):
        self.vectorizer = TfidfVectorizer(max_features=384)
        self.index_file = index_file
        self.documents_file = documents_file

        # Создаем директорию для хранения файлов, если её нет
        os.makedirs(os.path.dirname(index_file), exist_ok=True)

        self.index = self._load_index()
        self.documents = self._load_documents()
        self.is_vectorizer_fitted = False

    def create_embedding(self, text):
        """Создание векторного представления текста"""
        try:
            if not self.is_vectorizer_fitted:
                # Если векторайзер еще не обучен, обучаем его на текущем тексте
                vectors = self.vectorizer.fit_transform([text])
                self.is_vectorizer_fitted = True
            else:
                # Если векторайзер уже обучен, просто трансформируем текст
                vectors = self.vectorizer.transform([text])

            # Преобразуем разреженную матрицу в плотный вектор
            embedding = vectors.toarray()[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддинга: {e}")
            raise

    def add_document(self, text, document_id):
        """Добавление документа в индекс"""
        try:
            if text.strip():
                self.documents.append({
                    'id': document_id,
                    'text': text
                })
                embedding = self.create_embedding(text)
                embedding_array = np.array([embedding]).astype('float32')
                self.index.add(embedding_array)
                logger.info(f"Документ {document_id} успешно добавлен в базу")
                self.save()
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении документа: {e}")
            return False

    def search(self, query, top_k=3):
        """Поиск похожих документов"""
        try:
            query_embedding = self.create_embedding(query)
            query_embedding = np.array([query_embedding]).astype('float32')
            distances, indices = self.index.search(query_embedding, top_k)
            results = []
            for idx in indices[0]:
                if idx < len(self.documents):
                    results.append(self.documents[idx])
            return results
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return []

    def save(self):
        """Сохранение индекса и документов"""
        try:
            self._save_index()
            self._save_documents()
        except Exception as e:
            logger.error(f"Ошибка при сохранении базы: {e}")

    def _load_index(self):
        """Загрузка индекса"""
        try:
            if os.path.exists(self.index_file):
                logger.info(f"Загрузка индекса из файла: {self.index_file}")
                return faiss.read_index(self.index_file)
            logger.info("Создание нового индекса")
            return faiss.IndexFlatL2(384)  # Используем размерность TfidfVectorizer
        except Exception as e:
            logger.error(f"Ошибка при загрузке индекса: {e}")
            return faiss.IndexFlatL2(384)

    def _save_index(self):
        """Сохранение индекса"""
        try:
            faiss.write_index(self.index, self.index_file)
            logger.info(f"Индекс сохранён в файл: {self.index_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении индекса: {e}")

    def _load_documents(self):
        """Загрузка документов"""
        try:
            if os.path.exists(self.documents_file):
                logger.info(f"Загрузка документов из файла: {self.documents_file}")
                with open(self.documents_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            logger.info("Создание нового списка документов")
            return []
        except Exception as e:
            logger.error(f"Ошибка при загрузке документов: {e}")
            return []

    def _save_documents(self):
        """Сохранение документов"""
        try:
            with open(self.documents_file, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=4)
            logger.info(f"Документы сохранены в файл: {self.documents_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении документов: {e}")