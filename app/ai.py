import os
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Dict, Any, Optional
import json
import hashlib
import requests
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

# Инициализируем модель для embeddings
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

class GigaChatAPI:
    """Класс для работы с GigaChat API"""

    def __init__(self):
        self.api_key = os.environ.get('GIGACHAT_API_KEY')
        if not self.api_key:
            logger.error("GIGACHAT_API_KEY не найден в переменных окружения")
            raise ValueError("GIGACHAT_API_KEY не найден")

        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.token = None

    def _get_token(self) -> Optional[str]:
        """Получение токена для доступа к API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = requests.post(
                f"{self.base_url}/oauth/token",
                headers=headers,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()
            return data.get('access_token')

        except Exception as e:
            logger.error(f"Ошибка при получении токена: {str(e)}")
            raise

    def generate_response(self, prompt: str) -> str:
        """Генерация ответа с использованием GigaChat API"""
        try:
            if not self.token:
                self.token = self._get_token()

            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            data = {
                'model': 'GigaChat:latest',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Ты - интеллектуальный помощник, который отвечает на вопросы по контексту. Если ответа нет в контексте, отвечай, что не нашел информацию. Каждую информацию адаптируй под ответ для пользователя.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.7,
                'max_tokens': 1500
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' in result and result['choices']:
                answer = result['choices'][0]['message']['content']
                logger.info("Успешно получен ответ от GigaChat API")
                return answer
            else:
                logger.error("Неверный формат ответа от API")
                raise ValueError("Неверный формат ответа от API")

        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            raise

MAX_RESPONSE_LENGTH = 3000  # Maximum length for a single response message
MAX_RESULTS = 2  # Limit number of results to keep response concise

def get_embedding(text: str) -> np.ndarray:
    """Получить векторное представление текста"""
    return model.encode([text])[0]

def truncate_text(text: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
    """Обрезать текст до указанной длины, сохраняя целостность предложений"""
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    last_period = truncated.rfind('.')

    if last_period > 0:
        return truncated[:last_period + 1]
    return truncated[:max_length] + "..."

def answer_question(question: str, vector_db_path: str) -> str:
    """
    Ответить на вопрос, используя векторную базу данных и GigaChat
    """
    try:
        logger.info(f"Попытка ответить на вопрос: {question}")

        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(vector_db_path, "vector_index.faiss"),
            os.path.join(vector_db_path, "documents.json")
        )

        # Ищем похожие документы
        results = vector_db.search(question, top_k=MAX_RESULTS)
        logger.info(f"Найдено документов: {len(results)}")

        if not results:
            return "К сожалению, я не нашел информации по вашему вопросу в доступных материалах. Попробуйте переформулировать вопрос или уточнить, что именно вас интересует."

        # Формируем контекст из найденных документов
        context = ""
        for result in results:
            if isinstance(result, dict) and 'text' in result:
                text = result['text'].replace('\n', ' ').replace('\r', '')
                text = ' '.join(text.split())
                context += text + "\n\n"
            else:
                text = str(result).replace('\n', ' ').replace('\r', '')
                text = ' '.join(text.split())
                context += text + "\n\n"

        # Формируем промпт для GigaChat
        prompt = f"""
Вопрос пользователя: {question}

Контекст:
{context}

Пожалуйста, сформируй понятный и структурированный ответ на основе предоставленного контекста."""

        try:
            # Получаем ответ от GigaChat
            gigachat = GigaChatAPI()
            response = gigachat.generate_response(prompt)

            # Обрезаем ответ, если он слишком длинный
            final_response = truncate_text(response)
            logger.info("Ответ успешно сформирован через GigaChat")
            return final_response

        except Exception as e:
            logger.error(f"Ошибка при получении ответа от GigaChat: {str(e)}")
            return "Извините, произошла ошибка при обработке вашего вопроса. Пожалуйста, попробуйте еще раз или обратитесь к администратору."

    except Exception as e:
        logger.error(f"Ошибка в answer_question: {str(e)}")
        return "Извините, произошла ошибка при поиске ответа на ваш вопрос. Пожалуйста, попробуйте еще раз или обратитесь к администратору системы."

def generate_document_id(file_path: str, text: str, index: int) -> str:
    """Генерирует уникальный ID документа"""
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{file_path}_{index}_{text_hash}"

def add_file_to_vector_db(file_path: str, save_path: str) -> bool:
    """Обработать файл и добавить его содержимое в векторную базу данных"""
    try:
        logger.info(f"Начало обработки файла для добавления в векторную БД: {file_path}")
        os.makedirs(save_path, exist_ok=True)

        from app.file_processing import process_file
        documents = process_file(file_path)

        if not documents:
            logger.error(f"Не удалось извлечь документы из файла: {file_path}")
            return False

        logger.info(f"Извлечено {len(documents)} документов из файла")

        vector_db = VectorDB(
            os.path.join(save_path, "vector_index.faiss"),
            os.path.join(save_path, "documents.json")
        )

        success_count = 0
        for idx, doc in enumerate(documents):
            try:
                if isinstance(doc, str):
                    text = doc
                else:
                    text = doc.get('text', '')

                if text:
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