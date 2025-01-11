import os
import logging
from sentence_transformers import SentenceTransformer
from gigachat import GigaChat
import faiss
import numpy as np
from app.services.file_processor import FileProcessor

logger = logging.getLogger(__name__)

class AIProcessor:
    _instance = None
    _embedding_model = None
    _index = None
    _documents = {}

    def __init__(self):
        self.model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        self.vector_store_path = os.path.join(os.getcwd(), 'app', 'data', 'vector_store')
        os.makedirs(self.vector_store_path, exist_ok=True)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIProcessor()
        return cls._instance

    def _get_embedding_model(self):
        if self._embedding_model is None:
            try:
                self._embedding_model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели: {str(e)}")
                return None
        return self._embedding_model

    def _get_llm(self):
        try:
            llm = GigaChat(
                credentials=os.environ.get("GIGACHAT_API_KEY"),
                verify_ssl_certs=False
            )
            return llm
        except Exception as e:
            logger.error(f"Ошибка при инициализации GigaChat: {str(e)}")
            return None

    def add_file_to_vector_db(self, file_path, course_id):
        """Добавляет файл в векторную базу данных"""
        try:
            logger.info(f"Добавление файла {file_path} в векторную базу для курса {course_id}")

            # Обработка файла и получение текста
            text = FileProcessor.process_file(file_path)
            if not text:
                logger.error("Не удалось обработать файл")
                return False

            # Получаем модель для эмбеддингов
            model = self._get_embedding_model()
            if not model:
                return False

            # Создаем векторное представление
            try:
                embedding = model.encode([text])[0]
            except Exception as e:
                logger.error(f"Ошибка при создании эмбеддинга: {str(e)}")
                return False

            # Путь для сохранения векторной базы данных курса
            course_vector_path = os.path.join(self.vector_store_path, str(course_id))
            os.makedirs(course_vector_path, exist_ok=True)

            # Инициализируем или загружаем индекс
            index_path = os.path.join(course_vector_path, 'faiss.index')
            if os.path.exists(index_path):
                try:
                    self._index = faiss.read_index(index_path)
                    # Загружаем существующие документы
                    docs_path = os.path.join(course_vector_path, 'documents.npy')
                    if os.path.exists(docs_path):
                        self._documents = np.load(docs_path, allow_pickle=True).item()
                except Exception as e:
                    logger.error(f"Ошибка при загрузке индекса: {str(e)}")
                    return False
            else:
                self._index = faiss.IndexFlatL2(embedding.shape[0])
                self._documents = {}

            # Добавляем новый документ
            doc_id = len(self._documents)
            self._documents[doc_id] = text
            self._index.add(embedding.reshape(1, -1))

            # Сохраняем обновленный индекс и документы
            try:
                faiss.write_index(self._index, index_path)
                np.save(os.path.join(course_vector_path, 'documents.npy'), self._documents)
                logger.info(f"Векторная база обновлена и сохранена для курса {course_id}")
                return True
            except Exception as e:
                logger.error(f"Ошибка при сохранении индекса: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при добавлении файла в векторную базу: {str(e)}")
            return False

    def answer_question(self, query, course_id):
        """Отвечает на вопрос, используя материалы курса"""
        try:
            logger.info(f"Поиск ответа на вопрос для курса {course_id}")

            # Путь к векторной базе курса
            course_vector_path = os.path.join(self.vector_store_path, str(course_id))
            if not os.path.exists(course_vector_path):
                logger.error(f"Векторная база для курса {course_id} не найдена")
                return None

            # Загружаем индекс и документы
            try:
                self._index = faiss.read_index(os.path.join(course_vector_path, 'faiss.index'))
                self._documents = np.load(os.path.join(course_vector_path, 'documents.npy'), allow_pickle=True).item()
            except Exception as e:
                logger.error(f"Ошибка при загрузке векторной базы: {str(e)}")
                return None

            # Получаем эмбеддинг запроса
            model = self._get_embedding_model()
            if not model:
                return None

            query_embedding = model.encode([query])[0]

            # Ищем похожие документы
            k = 3  # количество ближайших документов
            distances, indices = self._index.search(query_embedding.reshape(1, -1), k)

            # Формируем контекст из найденных документов
            context = "\n".join([self._documents[idx] for idx in indices[0]])

            # Получаем LLM модель
            llm = self._get_llm()
            if not llm:
                return None

            # Формируем промпт
            prompt = f"""Ответь на вопрос пользователя, используя только информацию из предоставленного контекста. 
Если в контексте нет информации для ответа, сообщи об этом.

Контекст:
{context}

Вопрос:
{query}

Ответ:"""

            # Получаем ответ от модели
            try:
                response = llm.chat([
                    {"role": "system", "content": "Отвечай кратко и по существу на русском языке."},
                    {"role": "user", "content": prompt}
                ])
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Ошибка при генерации ответа: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при поиске ответа на вопрос: {str(e)}")
            return None