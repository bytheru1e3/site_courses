import os
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Dict, Any
import json
from app.services.vector_db import VectorDB
import hashlib

logger = logging.getLogger(__name__)

# Инициализируем модель для embeddings
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

def get_embedding(text: str) -> np.ndarray:
    """Получить векторное представление текста"""
    return model.encode([text])[0]

def generate_document_id(file_path: str, text: str, index: int) -> str:
    """
    Генерирует уникальный ID документа на основе пути к файлу, текста и индекса
    """
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{file_path}_{index}_{text_hash}"

def add_file_to_vector_db(file_path: str, save_path: str) -> bool:
    """
    Обработать файл и добавить его содержимое в векторную базу данных
    """
    try:
        logger.info(f"Начало обработки файла для добавления в векторную БД: {file_path}")

        # Проверяем существование директорий
        os.makedirs(save_path, exist_ok=True)

        from app.file_processing import process_file
        documents = process_file(file_path)

        if not documents:
            logger.error(f"Не удалось извлечь документы из файла: {file_path}")
            return False

        logger.info(f"Извлечено {len(documents)} документов из файла")

        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(save_path, "vector_index.faiss"),
            os.path.join(save_path, "documents.json")
        )

        # Добавляем документы в базу
        success_count = 0
        for idx, doc in enumerate(documents):
            if isinstance(doc, str):
                text = doc
            else:
                text = doc.get('text', '')

            if text:
                # Генерируем уникальный ID для документа
                document_id = generate_document_id(file_path, text, idx)
                if vector_db.add_document(text, document_id):
                    success_count += 1
                    logger.info(f"Документ {idx + 1}/{len(documents)} успешно добавлен")
                else:
                    logger.warning(f"Не удалось добавить документ {idx + 1}/{len(documents)}")

        logger.info(f"Успешно добавлено {success_count} из {len(documents)} документов в векторную БД")
        return success_count > 0

    except Exception as e:
        logger.error(f"Ошибка в add_file_to_vector_db: {str(e)}")
        return False

def answer_question(question: str, vector_db_path: str) -> str:
    """
    Ответить на вопрос, используя векторную базу данных
    """
    try:
        logger.info(f"Попытка ответить на вопрос с использованием векторной БД: {question}")

        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(vector_db_path, "vector_index.faiss"),
            os.path.join(vector_db_path, "documents.json")
        )

        # Ищем похожие документы
        results = vector_db.search(question, top_k=3)

        if not results:
            logger.warning("Не найдено релевантных документов для ответа")
            return "К сожалению, не удалось найти релевантную информацию для ответа на ваш вопрос."

        # Формируем ответ из найденных документов
        response = "На основе найденных материалов:\n\n"
        for i, doc in enumerate(results, 1):
            if isinstance(doc, dict) and 'text' in doc:
                response += f"{i}. {doc['text']}\n\n"
            else:
                response += f"{i}. {doc}\n\n"

        logger.info("Ответ успешно сформирован")
        return response

    except Exception as e:
        logger.error(f"Ошибка в answer_question: {str(e)}")
        return "Произошла ошибка при поиске ответа на ваш вопрос."