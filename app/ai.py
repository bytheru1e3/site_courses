import os
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Dict, Any, Optional
import json
import hashlib
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models.gigachat import GigaChat
from langchain.chains import create_retrieval_chain
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

# Инициализируем модель для embeddings
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

class GigaChatAPI:
    """Класс для работы с GigaChat API через langchain"""
    def __init__(self):
        self.api_key = os.environ.get("GIGACHAT_API_KEY", "")
        if not self.api_key:
            logger.error("GIGACHAT_API_KEY не найден в переменных окружения")
            raise ValueError("GIGACHAT_API_KEY не найден")

        # Инициализация GigaChat через langchain
        self.llm = GigaChat(credentials=self.api_key,
                           verify_ssl_certs=False,
                           profanity_check=False)

        # Создаем промпт-шаблон
        self.prompt = ChatPromptTemplate.from_template("""Ответь на вопрос пользователя. \
Используй при этом только информацию из контекста. Если в контексте нет \
информации для ответа, сообщи об этом пользователю.
Контекст: {context}
Вопрос: {input}
Ответ:""")

    def generate_response(self, question: str, context: str) -> str:
        """
        Генерация ответа с использованием GigaChat через langchain
        """
        try:
            # Создаем цепочку документов
            document_chain = create_stuff_documents_chain(
                llm=self.llm,
                prompt=self.prompt
            )

            # Преобразуем контекст для langchain
            from langchain_core.documents import Document
            documents = [Document(page_content=context)]

            # Генерируем ответ
            response = document_chain.invoke({
                "input": question,
                "context": documents
            })

            return response['answer']

        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}", exc_info=True)
            raise

MAX_RESPONSE_LENGTH = 3000
MAX_RESULTS = 2

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

        try:
            # Создаем экземпляр GigaChatAPI и получаем ответ
            gigachat = GigaChatAPI()
            response = gigachat.generate_response(question, context)

            # Обрезаем ответ, если он слишком длинный
            final_response = truncate_text(response)
            logger.info("Ответ успешно сгенерирован через GigaChat")

            return final_response

        except Exception as e:
            logger.error(f"Ошибка при работе с GigaChat API: {str(e)}", exc_info=True)
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
    """
    Обработать файл и добавить его содержимое в векторную базу данных
    """
    try:
        logger.info(f"Начало обработки файла для добавления в векторную БД: {file_path}")
        os.makedirs(save_path, exist_ok=True)

        # Загружаем и обрабатываем файл в зависимости от его типа
        from app.file_processing import process_file
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document

        # Получаем текст из файла
        raw_documents = process_file(file_path)
        if not raw_documents:
            logger.error(f"Не удалось извлечь текст из файла: {file_path}")
            return False

        logger.info(f"Успешно извлечен текст из файла")

        # Разделяем текст на фрагменты
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        documents = []
        for doc in raw_documents:
            if isinstance(doc, str):
                text = doc
            else:
                text = doc.get('text', '')

            if text:
                # Создаем документы langchain с метаданными
                split_docs = text_splitter.split_text(text)
                for i, split_text in enumerate(split_docs):
                    doc_id = generate_document_id(file_path, split_text, i)
                    documents.append(
                        Document(
                            page_content=split_text,
                            metadata={
                                'source': file_path,
                                'chunk_id': i,
                                'doc_id': doc_id
                            }
                        )
                    )

        if not documents:
            logger.error("Не удалось создать документы для векторной БД")
            return False

        logger.info(f"Создано {len(documents)} документов для добавления в векторную БД")

        # Инициализируем или получаем векторную БД
        vector_db = VectorDB(
            os.path.join(save_path, "vector_index.faiss"),
            os.path.join(save_path, "documents.json")
        )

        # Добавляем документы в векторную БД
        success_count = 0
        for doc in documents:
            try:
                if vector_db.add_document(
                    doc.page_content,
                    doc.metadata['doc_id'],
                    metadata=doc.metadata
                ):
                    success_count += 1
                    logger.info(f"Документ {success_count}/{len(documents)} успешно добавлен")
            except Exception as e:
                logger.error(f"Ошибка при добавлении документа: {str(e)}")
                continue

        logger.info(f"Успешно добавлено {success_count} из {len(documents)} документов в векторную БД")
        return success_count > 0

    except Exception as e:
        logger.error(f"Ошибка в add_file_to_vector_db: {str(e)}", exc_info=True)
        return False