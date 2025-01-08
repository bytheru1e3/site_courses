import os
import numpy as np
from docx import Document
import PyPDF2
import logging

logger = logging.getLogger(__name__)

class FileProcessor:
    @staticmethod
    def process_file(file_path):
        """Извлекает текст из файла и создает векторное представление"""
        try:
            # Получаем расширение файла
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Извлекаем текст в зависимости от типа файла
            if file_ext == '.docx':
                text = FileProcessor._process_docx(file_path)
            elif file_ext == '.pdf':
                text = FileProcessor._process_pdf(file_path)
            else:
                raise ValueError(f"Неподдерживаемый тип файла: {file_ext}")

            # Создаем векторное представление (пока заглушка)
            vector = FileProcessor._create_vector(text)
            
            return vector

        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            raise

    @staticmethod
    def _process_docx(file_path):
        """Извлекает текст из DOCX файла"""
        try:
            doc = Document(file_path)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Ошибка при обработке DOCX файла: {str(e)}")
            raise

    @staticmethod
    def _process_pdf(file_path):
        """Извлекает текст из PDF файла"""
        try:
            text = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF файла: {str(e)}")
            raise

    @staticmethod
    def _create_vector(text):
        """
        Создает векторное представление текста
        В данной реализации возвращает случайный вектор
        """
        # Заглушка - возвращаем случайный вектор
        vector = np.random.rand(768).astype('float32')
        return vector.tolist()
