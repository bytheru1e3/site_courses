import os
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Dict, Any, Optional
import json
import hashlib
import requests
from app.services.vector_db import VectorDB
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    def _get_token(self) -> Optional[str]:
        """Получение токена для доступа к API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = self.session.post(
                f"{self.base_url}/oauth/token",
                headers=headers,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()
            return data.get('access_token')

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении токена: {str(e)}")
            raise

    def generate_response(self, prompt: str, max_retries: int = 3) -> str:
        """Генерация ответа с использованием GigaChat API"""
        retry_count = 0
        while retry_count < max_retries:
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
                            'content': (
                                'Ты - интеллектуальный помощник для обучающей платформы. '
                                'Твоя задача - анализировать предоставленный контекст и '
                                'формировать понятные, структурированные ответы на вопросы пользователей. '
                                'Используй факты только из предоставленного контекста. '
                                'Если информации недостаточно, честно признай это. '
                                'Форматируй ответ так, чтобы он был легко читаем.'
                            )
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.7,
                    'max_tokens': 1500
                }

                response = self.session.post(
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

            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при запросе к GigaChat API (попытка {retry_count + 1}): {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    self.token = None  # Reset token on error
                else:
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
        logger.info(f"Начало обработки вопроса: {question}")

        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(vector_db_path, "vector_index.faiss"),
            os.path.join(vector_db_path, "documents.json")
        )

        # Ищем похожие документы
        results = vector_db.search(question, top_k=2)
        logger.info(f"Найдено релевантных документов: {len(results)}")

        if not results:
            return ("Извините, я не нашел информации по вашему вопросу в доступных материалах. "
                   "Попробуйте переформулировать вопрос или уточнить, что именно вас интересует.")

        # Формируем контекст из найденных документов
        context = ""
        for result in results:
            if isinstance(result, dict) and 'text' in result:
                text = result['text'].replace('\n', ' ').strip()
                context += text + "\n\n"
            else:
                text = str(result).replace('\n', ' ').strip()
                context += text + "\n\n"

        # Формируем промпт для GigaChat
        prompt = f"""
Вопрос пользователя: {question}

Контекст из материалов курса:
{context}

Пожалуйста, сформируй понятный и структурированный ответ на основе предоставленного контекста. 
Используй только информацию из контекста. Если информации недостаточно, укажи это."""

        try:
            # Получаем ответ от GigaChat
            gigachat = GigaChatAPI()
            response = gigachat.generate_response(prompt)

            # Обрезаем ответ, если он слишком длинный
            final_response = truncate_text(response)
            logger.info("Ответ успешно сгенерирован через GigaChat")

            return final_response

        except Exception as e:
            logger.error(f"Ошибка при работе с GigaChat API: {str(e)}")
            return ("Извините, произошла техническая ошибка при обработке вашего вопроса. "
                   "Мы работаем над её устранением. Пожалуйста, попробуйте позже.")

    except Exception as e:
        logger.error(f"Критическая ошибка в answer_question: {str(e)}", exc_info=True)
        return ("Извините, произошла ошибка при поиске ответа на ваш вопрос. "
               "Пожалуйста, попробуйте позже или обратитесь к администратору системы.")

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