import os
import logging
from app.services.document_processor import DocumentProcessor
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

class FileProcessor:
    _vector_db = None
    _document_processor = None

    @classmethod
    def get_vector_db(cls):
        if cls._vector_db is None:
            cls._vector_db = VectorDB()
        return cls._vector_db

    @classmethod
    def get_document_processor(cls):
        if cls._document_processor is None:
            cls._document_processor = DocumentProcessor()
        return cls._document_processor

    @staticmethod
    def process_file(file_path):
        """Обработка файла и создание векторного представления"""
        try:
            logger.info(f"Начало обработки файла: {file_path}")

            # Получаем расширение файла
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext not in ['.docx', '.pdf']:
                raise ValueError(f"Неподдерживаемый тип файла: {file_ext}")

            # Обрабатываем файл через DocumentProcessor
            doc_processor = FileProcessor.get_document_processor()
            if doc_processor.process_file(file_path):
                logger.info(f"Файл {file_path} успешно обработан")
                return True
            else:
                logger.error(f"Не удалось обработать файл {file_path}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            return False

    @staticmethod
    def search_similar_documents(query, top_k=3):
        """Поиск похожих документов"""
        try:
            logger.info(f"Поиск документов по запросу: {query}")
            doc_processor = FileProcessor.get_document_processor()
            response = doc_processor.search_similar_documents(query, top_k)

            if response and 'answer' in response:
                # Форматируем ответ для пользователя
                return [{
                    'text': response['answer'],
                    'source': 'GigaChat'
                }]
            else:
                logger.warning("Не удалось получить ответ от GigaChat")
                # Используем fallback на обычный поиск через VectorDB
                vector_db = FileProcessor.get_vector_db()
                return vector_db.search(query, top_k)

        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {str(e)}")
            return []