import os
import json
import logging
from typing import Optional
import requests
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, vector_db_path: str):
        """Initialize AI service with vector database path"""
        # Создаем необходимые пути для индекса и документов
        os.makedirs(vector_db_path, exist_ok=True)
        index_path = os.path.join(vector_db_path, 'index.faiss')
        documents_path = os.path.join(vector_db_path, 'documents.json')

        self.vector_db = VectorDB(
            index_path=index_path,
            documents_path=documents_path
        )
        self.gigachat_api_key = os.environ.get('GIGACHAT_API_KEY')
        self._auth_token = None

    def _get_auth_token(self) -> Optional[str]:
        """Получение токена авторизации для GigaChat API"""
        try:
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            auth_headers = {
                "Authorization": f"Bearer {self.gigachat_api_key}",
                "RqUID": "test",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            response = requests.post(
                auth_url,
                headers=auth_headers,
                data="scope=GIGACHAT_API_PERS",
                verify=False
            )
            if response.status_code == 200:
                return response.json()['access_token']
            logger.error(f"Ошибка получения токена: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при авторизации в GigaChat: {str(e)}")
            return None

    def get_ai_response(self, question: str, course_title: str) -> str:
        """Получение ответа от GigaChat с учетом контекста курса"""
        try:
            # Поиск релевантного контекста
            results = self.vector_db.search(question)
            context = "\n".join([doc['text'] for doc in results]) if results else f"Контекст курса '{course_title}'"

            # Получение токена авторизации
            if not self._auth_token:
                self._auth_token = self._get_auth_token()

            if not self._auth_token:
                return "Извините, возникла проблема с подключением к сервису ИИ"

            # Формирование запроса к GigaChat
            prompt = f"""Контекст: {context}

            Вопрос: {question}

            Пожалуйста, дайте краткий и информативный ответ, основываясь на предоставленном контексте."""

            headers = {
                "Authorization": f"Bearer {self._auth_token}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "GigaChat:latest",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }

            response = requests.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers=headers,
                json=data,
                verify=False
            )

            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                return answer

            logger.error(f"Ошибка получения ответа от GigaChat: {response.status_code}")
            return "Извините, не удалось получить ответ от сервиса ИИ"

        except Exception as e:
            logger.error(f"Ошибка при получении ответа от ИИ: {str(e)}")
            return "Произошла ошибка при обработке вашего вопроса"