import os
import logging
from PyPDF2 import PdfReader
from docx import Document
import mammoth
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)

def split_into_chunks(text, chunk_size=4000):
    """Разделяет текст на чанки заданного размера"""
    chunks = []
    while len(text) > chunk_size:
        split_index = text[:chunk_size].rfind(" ")
        if split_index == -1:
            split_index = chunk_size
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        chunks.append(text)
    return chunks

class FileProcessor:
    _vector_db = None

    @classmethod
    def get_vector_db(cls):
        if cls._vector_db is None:
            cls._vector_db = VectorDBService()
        return cls._vector_db

    @staticmethod
    def process_file(file_path):
        """Обработка файла и создание векторного представления"""
        try:
            # Получаем расширение файла
            file_ext = os.path.splitext(file_path)[1].lower()

            # Извлекаем текст в зависимости от типа файла
            try:
                if file_ext == '.docx':
                    text = FileProcessor._process_docx(file_path)
                elif file_ext == '.pdf':
                    text = FileProcessor._process_pdf(file_path)
                else:
                    raise ValueError(f"Неподдерживаемый тип файла: {file_ext}")

                # Разбиваем текст на чанки
                chunks = split_into_chunks(text)

                # Создаем векторное представление и сохраняем в базу
                vector_db = FileProcessor.get_vector_db()

                # Обрабатываем каждый чанк текста
                vectors = []
                for chunk in chunks:
                    if chunk.strip():
                        vector = vector_db.process_document(file_path, chunk)
                        vectors.append(vector)

                logger.info(f"Файл {file_path} успешно обработан")
                return vectors

            except Exception as e:
                logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
                return []

        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            return []

    @staticmethod
    def _process_docx(file_path):
        """Извлекает текст из DOCX файла"""
        try:
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                text = result.value
                return text if text.strip() else "Документ пуст или не содержит текста"
        except Exception as e:
            logger.error(f"Ошибка при обработке DOCX файла: {str(e)}")
            return "Ошибка при чтении DOCX файла"

    @staticmethod
    def _process_pdf(file_path):
        """Извлекает текст из PDF файла"""
        try:
            text_parts = []
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)

            text = '\n'.join(text_parts)
            return text if text.strip() else "PDF документ пуст или не содержит текста"
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF файла: {str(e)}")
            return "Ошибка при чтении PDF файла"

    @staticmethod
    def search_similar_documents(query, top_k=3):
        """Поиск похожих документов"""
        try:
            vector_db = FileProcessor.get_vector_db()
            return vector_db.search_similar(query, top_k)
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {str(e)}")
            return []