import os
import json
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
import pickle

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self, index_path, documents_path):
        self.index_path = index_path
        self.documents_path = documents_path

        # Создаем директории если они не существуют
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(documents_path), exist_ok=True)

        self.documents = []
        self.index = None
        self.load()

        if self.index is None:
            self.index = faiss.IndexFlatL2(384)  # Размерность для модели sentence-transformers

        self.is_vectorizer_fitted = False
        self.vectorizer = TfidfVectorizer()

    def load(self):
        """Загрузка индекса и документов"""
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, 'rb') as f:
                    self.index = faiss.read_index(f)
                logger.info("Индекс успешно загружен")

            if os.path.exists(self.documents_path):
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                logger.info("Документы успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка при загрузке базы данных: {e}")
            self.index = None
            self.documents = []

    def create_embedding(self, text):
        try:
            if not text or not isinstance(text, str):
                logger.error("Получен невалидный текст для создания эмбеддинга")
                return np.zeros(384).astype('float32')

            if not self.is_vectorizer_fitted:
                vectors = self.vectorizer.fit_transform([text])
                self.is_vectorizer_fitted = True
            else:
                vectors = self.vectorizer.transform([text])

            # Нормализуем вектор к нужной размерности
            embedding = vectors.toarray()[0]
            if len(embedding) > 384:
                embedding = embedding[:384]
            elif len(embedding) < 384:
                embedding = np.pad(embedding, (0, 384 - len(embedding)))

            return embedding.astype('float32')
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддинга: {e}")
            return np.zeros(384).astype('float32')

    def add_document(self, text, document_id):
        """Добавление документа в индекс"""
        try:
            if text and isinstance(text, str):
                if not any(doc['id'] == document_id for doc in self.documents):
                    self.documents.append({
                        'id': document_id,
                        'text': text
                    })
                    embedding = self.create_embedding(text)
                    embedding_array = np.array([embedding])
                    self.index.add(embedding_array)
                    logger.info(f"Документ {document_id} успешно добавлен в базу")
                    self.save()
                    return True
                else:
                    logger.warning(f"Документ {document_id} уже существует в базе")
            return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении документа: {e}")
            return False

    def save(self):
        """Сохранение индекса и документов"""
        try:
            with open(self.index_path, 'wb') as f:
                faiss.write_index(self.index, f)
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents, f)
            logger.info("База данных успешно сохранена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении базы данных: {e}")
            return False

    def search(self, query, top_k=3):
        """Поиск похожих документов"""
        try:
            if not query or not isinstance(query, str):
                return []

            query_embedding = self.create_embedding(query)
            query_embedding = np.array([query_embedding])

            if self.index.ntotal == 0:
                logger.warning("База данных пуста")
                return []

            distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

            results = []
            for idx in indices[0]:
                if idx >= 0 and idx < len(self.documents):
                    results.append(self.documents[idx])
            return results
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return []

    def remove_document(self, document_id):
        """Удаление документа из индекса"""
        try:
            # Находим индекс документа в списке
            doc_idx = None
            for idx, doc in enumerate(self.documents):
                if doc['id'] == document_id:
                    doc_idx = idx
                    break

            if doc_idx is not None:
                # Удаляем документ из списка
                self.documents.pop(doc_idx)

                # Создаем новый индекс
                new_index = faiss.IndexFlatL2(384)

                # Переиндексируем оставшиеся документы
                for doc in self.documents:
                    embedding = self.create_embedding(doc['text'])
                    embedding_array = np.array([embedding]).astype('float32')
                    new_index.add(embedding_array)

                # Заменяем старый индекс новым
                self.index = new_index
                self.save()

                logger.info(f"Документ {document_id} успешно удален из базы")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении документа: {e}")
            return False