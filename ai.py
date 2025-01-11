import os
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import logging
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

def get_embedding(text: str) -> np.ndarray:
    """Получить векторное представление текста"""
    return model.encode([text])[0]

def add_file_to_vector_db(file_path: str, save_path: str) -> bool:
    """
    Обработать файл и добавить его содержимое в векторную базу данных
    """
    try:
        from file_processing import process_file
        documents = process_file(file_path, chunk_size=500, overlap=100)

        if not documents:
            logger.error(f"No documents extracted from {file_path}")
            return False

        # Создаем векторные представления для всех документов
        vectors = []
        metadata = []

        for doc in documents:
            try:
                vector = get_embedding(doc['text'])
                vectors.append(vector)
                metadata.append({
                    'text': doc['text'],
                    'source': file_path
                })
            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                continue

        if not vectors:
            logger.error("No vectors created")
            return False

        vectors = np.array(vectors).astype('float32')

        # Создаем или загружаем индекс FAISS
        dimension = vectors.shape[1]
        if os.path.exists(save_path):
            index = faiss.read_index(os.path.join(save_path, "vectors.index"))
            with open(os.path.join(save_path, "metadata.json"), 'r') as f:
                existing_metadata = json.load(f)
        else:
            os.makedirs(save_path, exist_ok=True)
            index = faiss.IndexFlatL2(dimension)
            existing_metadata = []

        # Добавляем новые векторы в индекс
        index.add(vectors)

        # Сохраняем обновленный индекс и метаданные
        faiss.write_index(index, os.path.join(save_path, "vectors.index"))

        existing_metadata.extend(metadata)
        with open(os.path.join(save_path, "metadata.json"), 'w') as f:
            json.dump(existing_metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"Successfully processed and indexed file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error in add_file_to_vector_db: {str(e)}")
        return False

def answer_question(question: str, vector_db_path: str) -> str:
    """
    Ответить на вопрос, используя векторную базу данных
    """
    try:
        # Загружаем индекс и метаданные
        index = faiss.read_index(os.path.join(vector_db_path, "vectors.index"))
        with open(os.path.join(vector_db_path, "metadata.json"), 'r') as f:
            metadata = json.load(f)

        # Получаем векторное представление вопроса
        question_vector = get_embedding(question)

        # Ищем похожие документы
        k = 3  # количество похожих документов
        D, I = index.search(np.array([question_vector]).astype('float32'), k)

        # Формируем ответ на основе найденных документов
        relevant_docs = [metadata[i] for i in I[0] if i < len(metadata)]

        if not relevant_docs:
            return "К сожалению, не удалось найти релевантную информацию для ответа на ваш вопрос."

        response = "На основе найденных материалов:\n\n"
        for i, doc in enumerate(relevant_docs, 1):
            response += f"{i}. {doc['text']}\n\n"

        return response

    except Exception as e:
        logger.error(f"Error in answer_question: {str(e)}")
        return "Произошла ошибка при поиске ответа на ваш вопрос."

if __name__ == "__main__":
    # Пример использования
    vector_db_path = os.path.join(os.getcwd(), "app", "data", "vector_store")
    question = "Что такое векторная база данных?"
    print(answer_question(question, vector_db_path))