import os
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Dict, Any
import json
import hashlib
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

# Инициализируем модель для embeddings
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

MAX_RESPONSE_LENGTH = 3000  # Maximum length for a single response message
MAX_RESULTS = 2  # Limit number of results to keep response concise

SYSTEM_PROMPT = """
Ты интеллектуальный помощник, который отвечает на вопросы по контексту. 
Твоя задача:
1. Отвечать ТОЛЬКО на основе предоставленной информации из контекста
2. Если ответа нет в контексте, честно сообщить об этом
3. Адаптировать информацию под пользователя, делая её понятной и доступной
4. Использовать вежливый и дружелюбный тон
5. Давать краткие, но информативные ответы
"""

def get_embedding(text: str) -> np.ndarray:
    """Получить векторное представление текста"""
    return model.encode([text])[0]

def truncate_text(text: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
    """Обрезать текст до указанной длины, сохраняя целостность предложений"""
    if len(text) <= max_length:
        return text

    # Находим последнюю точку перед максимальной длиной
    truncated = text[:max_length]
    last_period = truncated.rfind('.')

    if last_period > 0:
        return truncated[:last_period + 1]
    return truncated[:max_length] + "..."

def answer_question(question: str, vector_db_path: str) -> str:
    """
    Ответить на вопрос, используя векторную базу данных
    """
    try:
        logger.info(f"Попытка ответить на вопрос: {question}")

        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(vector_db_path, "vector_index.faiss"),
            os.path.join(vector_db_path, "documents.json")
        )

        # Ищем похожие документы, ограничиваем количество результатов
        results = vector_db.search(question, top_k=MAX_RESULTS)
        logger.info(f"Найдено документов: {len(results)}")

        if not results:
            return "К сожалению, я не нашел информации по вашему вопросу в доступных материалах. Попробуйте переформулировать вопрос или уточнить, что именно вас интересует."

        # Формируем контекст для ответа
        context = ""
        for result in results:
            if isinstance(result, dict) and 'text' in result:
                context += result['text'] + "\n\n"
            else:
                context += str(result) + "\n\n"

        # Готовим финальный ответ с учетом системного промпта
        response = f"На основе найденных материалов, отвечаю на ваш вопрос:\n\n"
        response += context

        # Обрезаем ответ, если он слишком длинный
        final_response = truncate_text(response)
        logger.info("Ответ успешно сформирован")
        return final_response

    except Exception as e:
        logger.error(f"Ошибка в answer_question: {str(e)}")
        return "Извините, произошла ошибка при поиске ответа на ваш вопрос. Пожалуйста, попробуйте еще раз или обратитесь к администратору системы."

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
            try:
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
            except Exception as e:
                logger.error(f"Ошибка при добавлении документа {idx + 1}: {str(e)}")
                continue

        logger.info(f"Успешно добавлено {success_count} из {len(documents)} документов в векторную БД")
        return success_count > 0

    except Exception as e:
        logger.error(f"Ошибка в add_file_to_vector_db: {str(e)}")
        return False