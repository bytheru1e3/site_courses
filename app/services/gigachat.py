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
            logger.warning("GIGACHAT_API_KEY не найден в переменных окружения")
        
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.token = None

    def _get_token(self) -> Optional[str]:
        """Получение токена для доступа к API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.base_url}/oauth/token",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            else:
                logger.error(f"Ошибка получения токена: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении токена: {str(e)}")
            return None

    def generate_response(self, prompt: str) -> Optional[str]:
        """Генерация ответа с использованием GigaChat API"""
        try:
            if not self.token:
                self.token = self._get_token()
                if not self.token:
                    logger.error("Не удалось получить токен для доступа к API")
                    return None

            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'GigaChat:latest',
                'messages': [
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
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"Ошибка генерации ответа: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            return None
