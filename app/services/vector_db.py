import os
import pickle
import json
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
from sentence_transformers import SentenceTransformer
import traceback

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self, index_path, documents_path):
        self.index_path = index_path
        self.documents_path = documents_path
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
        self.embedding_dim = 768  # Размерность для модели paraphrase-multilingual-mpnet-base-v2

        # Создаем директории если они не существуют
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(documents_path), exist_ok=True)

        self.documents = []
        self.index = None
        self.load()

        if self.index is None:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            logger.info(f"Created new FAISS index with dimension {self.embedding_dim}")

    def load(self):
        """Загрузка индекса и документов"""
        try:
            if os.path.exists(self.index_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    logger.info("Индекс успешно загружен")
                except Exception as e:
                    logger.error(f"Ошибка при чтении индекса: {str(e)}")
                    self.index = None
            else:
                logger.warning(f"Индекс не найден по пути: {self.index_path}")

            if os.path.exists(self.documents_path):
                try:
                    with open(self.documents_path, 'rb') as f:
                        self.documents = pickle.load(f)
                    logger.info(f"Документы успешно загружены, количество: {len(self.documents)}")
                except Exception as e:
                    logger.error(f"Ошибка при чтении документов: {str(e)}")
                    self.documents = []
            else:
                logger.warning(f"Файл документов не найден по пути: {self.documents_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке базы данных: {e}\n{traceback.format_exc()}")
            self.index = None
            self.documents = []

    def create_embedding(self, text):
        """Создание эмбеддинга текста с помощью sentence-transformers"""
        try:
            if not text or not isinstance(text, str):
                logger.error("Получен невалидный текст для создания эмбеддинга")
                return None

            # Используем sentence-transformers для создания эмбеддинга
            embedding = self.model.encode([text])[0]
            return embedding.astype('float32')
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддинга: {e}\n{traceback.format_exc()}")
            return None

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

                # Проверяем размерность эмбеддинга
                if embedding.shape[0] != self.embedding_dim:
                    logger.error(f"Неверная размерность эмбеддинга: {embedding.shape[0]}, ожидается {self.embedding_dim}")
                    return False

                # Добавляем документ в список
                self.documents.append({
                    'id': document_id,
                    'text': text
                })

                try:
                    # Добавляем эмбеддинг в индекс
                    embedding_array = np.array([embedding])
                    self.index.add(embedding_array)
                except Exception as e:
                    logger.error(f"Ошибка при добавлении эмбеддинга в индекс: {e}\n{traceback.format_exc()}")
                    # Удаляем документ из списка, так как не удалось добавить в индекс
                    self.documents.pop()
                    return False

                # Сохраняем изменения
                if not self.save():
                    # Если не удалось сохранить, откатываем изменения
                    self.documents.pop()
                    return False

                logger.info(f"Документ {document_id} успешно добавлен в базу")
                return True
            else:
                logger.warning(f"Документ {document_id} уже существует в базе")
            return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении документа: {e}\n{traceback.format_exc()}")
            return False

    def save(self):
        """Сохранение индекса и документов"""
        try:
            # Сохраняем индекс
            try:
                faiss.write_index(self.index, self.index_path)
                logger.info(f"Индекс сохранен в {self.index_path}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении индекса: {e}\n{traceback.format_exc()}")
                return False

            # Сохраняем документы
            try:
                with open(self.documents_path, 'wb') as f:
                    pickle.dump(self.documents, f)
                logger.info(f"Документы сохранены в {self.documents_path}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении документов: {e}\n{traceback.format_exc()}")
                return False

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении базы данных: {e}\n{traceback.format_exc()}")
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
            if query_embedding is None:
                logger.error("Не удалось создать эмбеддинг для запроса")
                return []

            query_embedding = np.array([query_embedding])

            # Ищем похожие документы
            try:
                distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
                logger.info(f"Найдено {len(indices[0])} документов для запроса")
            except Exception as e:
                logger.error(f"Ошибка при поиске в индексе: {e}\n{traceback.format_exc()}")
                return []

            results = []
            for idx in indices[0]:
                if idx >= 0 and idx < len(self.documents):
                    results.append(self.documents[idx])
            return results
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}\n{traceback.format_exc()}")
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
                new_index = faiss.IndexFlatL2(self.embedding_dim)

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