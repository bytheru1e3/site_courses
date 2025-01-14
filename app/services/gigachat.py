import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

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
                        'content': 'Ты - интеллектуальный ассистент. Анализируй контекст и давай четкие, структурированные ответы.'
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