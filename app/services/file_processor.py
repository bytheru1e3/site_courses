import os
from docx import Document
import PyPDF2
import logging
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

class FileProcessor:
    _vector_db = None

    @classmethod
    def get_vector_db(cls):
        if cls._vector_db is None:
            cls._vector_db = VectorDB()
        return cls._vector_db

    @staticmethod
    def process_file(file_path):
        """Извлекает текст из файла и создает векторное представление"""
        try:
            logger.info(f"Начало обработки файла: {file_path}")

            # Получаем расширение файла
            file_ext = os.path.splitext(file_path)[1].lower()

            # Извлекаем текст в зависимости от типа файла
            text = ""
            try:
                if file_ext == '.docx':
                    text = FileProcessor._process_docx(file_path)
                elif file_ext == '.pdf':
                    text = FileProcessor._process_pdf(file_path)
                else:
                    raise ValueError(f"Неподдерживаемый тип файла: {file_ext}")

                if not text.strip():
                    raise ValueError("Не удалось извлечь текст из файла")

                logger.info(f"Текст успешно извлечен из файла {file_path}")

            except Exception as e:
                logger.error(f"Ошибка при извлечении текста из файла {file_path}: {str(e)}")
                return None

            # Создаем векторное представление и добавляем в базу
            try:
                vector_db = FileProcessor.get_vector_db()
                logger.info(f"Создание векторного представления для файла {file_path}")

                vector = vector_db.create_embedding(text)
                if not vector:
                    logger.error(f"Не удалось создать векторное представление для файла {file_path}")
                    return None

                logger.info(f"Векторное представление создано для файла {file_path}")

                # Добавляем документ в векторную базу
                if vector_db.add_document(text, file_path):
                    logger.info(f"Файл {file_path} успешно добавлен в векторную базу")
                    return vector
                else:
                    logger.error(f"Не удалось добавить файл {file_path} в векторную базу")
                    return None

            except Exception as e:
                logger.error(f"Ошибка при создании векторного представления: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            return None

    @staticmethod
    def _process_docx(file_path):
        """Извлекает текст из DOCX файла"""
        try:
            logger.info(f"Начало обработки DOCX файла: {file_path}")
            text_parts = []
            doc = Document(file_path)

            # Извлекаем текст из параграфов
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            # Извлекаем текст из таблиц
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)

            text = '\n'.join(text_parts)
            if not text.strip():
                logger.warning(f"DOCX файл {file_path} не содержит текста")
                return ""

            logger.info(f"DOCX файл {file_path} успешно обработан")
            return text

        except Exception as e:
            logger.error(f"Ошибка при обработке DOCX файла {file_path}: {str(e)}")
            raise

    @staticmethod
    def _process_pdf(file_path):
        """Извлекает текст из PDF файла"""
        try:
            logger.info(f"Начало обработки PDF файла: {file_path}")
            text_parts = []

            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)

            text = '\n'.join(text_parts)
            if not text.strip():
                logger.warning(f"PDF файл {file_path} не содержит текста")
                return ""

            logger.info(f"PDF файл {file_path} успешно обработан")
            return text

        except Exception as e:
            logger.error(f"Ошибка при обработке PDF файла {file_path}: {str(e)}")
            raise

    @staticmethod
    def search_similar_documents(query, top_k=3):
        """Поиск похожих документов"""
        try:
            logger.info(f"Поиск документов по запросу: {query}")
            vector_db = FileProcessor.get_vector_db()
            results = vector_db.search(query, top_k)
            logger.info(f"Найдено {len(results)} документов")
            return results
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {str(e)}")
            return []