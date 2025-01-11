import os
import logging
from docx import Document
import PyPDF2

logger = logging.getLogger(__name__)

class FileProcessor:
    @staticmethod
    def process_file(file_path):
        """Извлекает текст из файла"""
        try:
            logger.info(f"Начало обработки файла: {file_path}")

            # Получаем расширение файла
            file_ext = os.path.splitext(file_path)[1].lower()

            # Извлекаем текст в зависимости от типа файла
            if file_ext == '.docx':
                text = FileProcessor._process_docx(file_path)
            elif file_ext == '.pdf':
                text = FileProcessor._process_pdf(file_path)
            else:
                raise ValueError(f"Неподдерживаемый тип файла: {file_ext}")

            if not text.strip():
                raise ValueError("Не удалось извлечь текст из файла")

            logger.info(f"Текст успешно извлечен из файла {file_path}")
            return text

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
            logger.info(f"PDF файл {file_path} успешно обработан")
            return text

        except Exception as e:
            logger.error(f"Ошибка при обработке PDF файла {file_path}: {str(e)}")
            raise