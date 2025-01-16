import os
import json
import logging
import requests
from typing import Optional
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

        # Добавляем тестовые данные
        self._init_test_data()

    def _init_test_data(self):
        """Initialize test data in vector database"""
        if len(self.vector_db.documents) == 0:
            test_docs = [
                {
                    'id': 'test1',
                    'text': 'Это тестовый документ для демонстрации работы векторной базы данных.'
                },
                {
                    'id': 'test2',
                    'text': 'Система использует GigaChat API для обработки запросов пользователей.'
                }
            ]
            for doc in test_docs:
                self.vector_db.add_document(doc['text'], doc['id'])
            logger.info("Test data initialized successfully")

    def _get_auth_token(self) -> Optional[str]:
        """Получение токена авторизации для GigaChat API"""
        try:
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            auth_headers = {
                "Authorization": f"Bearer {self.gigachat_api_key}",
                "RqUID": "test",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            logger.debug(f"Attempting to get auth token from GigaChat API")
            response = requests.post(
                auth_url,
                headers=auth_headers,
                data="scope=GIGACHAT_API_PERS",
                verify=False
            )

            if response.status_code == 200:
                token = response.json().get('access_token')
                if token:
                    logger.info("Successfully obtained GigaChat auth token")
                    return token
                logger.error("Auth token not found in response")
                return None

            logger.error(f"Failed to get auth token. Status: {response.status_code}, Response: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error during GigaChat authentication: {str(e)}")
            return None

    def get_ai_response(self, question: str, course_title: str) -> str:
        """Получение ответа от GigaChat с учетом контекста курса"""
        try:
            # Поиск релевантного контекста
            results = self.vector_db.search(question)
            context = "\n".join([doc['text'] for doc in results]) if results else f"Контекст курса '{course_title}'"

            logger.debug(f"Retrieved context: {context}")

            # Получение токена авторизации
            if not self._auth_token:
                self._auth_token = self._get_auth_token()

            if not self._auth_token:
                logger.error("Failed to obtain auth token")
                return "Извините, возникла проблема с подключением к сервису ИИ. Пожалуйста, попробуйте позже."

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
                        "role": "system",
                        "content": "Вы - полезный ассистент, который помогает пользователям с их вопросами."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }

            logger.debug("Sending request to GigaChat API")
            response = requests.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers=headers,
                json=data,
                verify=False
            )

            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                logger.info("Successfully received response from GigaChat")
                return answer

            logger.error(f"Error from GigaChat API: Status {response.status_code}, Response: {response.text}")
            return "Извините, не удалось получить ответ от сервиса ИИ. Пожалуйста, попробуйте позже."

        except Exception as e:
            logger.error(f"Error in get_ai_response: {str(e)}")
            return "Произошла ошибка при обработке вашего вопроса. Пожалуйста, попробуйте позже."