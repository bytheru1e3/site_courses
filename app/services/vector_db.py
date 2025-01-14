import os
import pickle
import json
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self, index_path, documents_path):
        self.index_path = index_path
        self.documents_path = documents_path
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

        # Создаем директории если они не существуют
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(documents_path), exist_ok=True)

        self.documents = []
        self.index = None
        self.load()

        if self.index is None:
            self.index = faiss.IndexFlatL2(384)  # Размерность для модели sentence-transformers
            logger.info("Created new FAISS index")

    def load(self):
        """Загрузка индекса и документов"""
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                logger.info("Индекс успешно загружен")
            else:
                logger.warning(f"Индекс не найден по пути: {self.index_path}")

            if os.path.exists(self.documents_path):
                with open(self.documents_path, 'rb') as f:
                    self.documents = pickle.load(f)
                logger.info(f"Документы успешно загружены, количество: {len(self.documents)}")
            else:
                logger.warning(f"Файл документов не найден по пути: {self.documents_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке базы данных: {e}")
            self.index = None
            self.documents = []

    def create_embedding(self, text):
        """Создание эмбеддинга текста с помощью sentence-transformers"""
        try:
            if not text or not isinstance(text, str):
                logger.error("Получен невалидный текст для создания эмбеддинга")
                return np.zeros(384).astype('float32')

            # Используем sentence-transformers для создания эмбеддинга
            embedding = self.model.encode([text])[0]
            return embedding.astype('float32')
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддинга: {e}")
            return np.zeros(384).astype('float32')

    def add_document(self, text, document_id):
        """Добавление документа в индекс"""
        try:
            if not text or not isinstance(text, str):
                logger.error(f"Получен невалидный текст для документа {document_id}")
                return False

            # Проверяем, нет ли уже такого документа
            if not any(doc.get('id') == document_id for doc in self.documents):
                logger.info(f"Добавление нового документа с ID: {document_id}")

                # Создаем эмбеддинг
                embedding = self.create_embedding(text)
                if embedding is None:
                    logger.error(f"Не удалось создать эмбеддинг для документа {document_id}")
                    return False

                # Добавляем документ в список
                self.documents.append({
                    'id': document_id,
                    'text': text
                })

                # Добавляем эмбеддинг в индекс
                embedding_array = np.array([embedding])
                self.index.add(embedding_array)

                # Сохраняем изменения
                self.save()
                logger.info(f"Документ {document_id} успешно добавлен в базу")
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
            # Сохраняем индекс
            faiss.write_index(self.index, self.index_path)
            logger.info(f"Индекс сохранен в {self.index_path}")

            # Сохраняем документы
            with open(self.documents_path, 'wb') as f:
                pickle.dump(self.documents, f)
            logger.info(f"Документы сохранены в {self.documents_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении базы данных: {e}")
            return False

    def search(self, query, top_k=3):
        """Поиск похожих документов"""
        try:
            if not query or not isinstance(query, str):
                logger.error("Получен невалидный запрос для поиска")
                return []

            if self.index.ntotal == 0:
                logger.warning("База данных пуста")
                return []

            # Создаем эмбеддинг запроса
            query_embedding = self.create_embedding(query)
            query_embedding = np.array([query_embedding])

            # Ищем похожие документы
            distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
            logger.info(f"Найдено {len(indices[0])} документов для запроса")

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