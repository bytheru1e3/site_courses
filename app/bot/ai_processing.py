# File: ai_processing.py
import os
import hashlib
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from sentence_transformers import CrossEncoder
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models.gigachat import GigaChat

class VectorDatabase:
    def __init__(self, file_path: str = 'data/kurs.txt'):
        self.file_path = file_path
        self.embeddings = None
        self.vector_db = None
        self.texts = []
        self.cross_encoder = CrossEncoder('DiTy/cross-encoder-russian-msmarco')
        self.llm = self._init_gigachat()
        self._initialize_embeddings()
        self._load_vector_db()

    def _init_gigachat(self):
        return GigaChat(
            credentials="OGJmNTY1ZjItOTgwOS00ZjMyLTk3MmUtMjNhMjYxYmNmOTA3OjQwMTAyMTQyLWQxYmItNDRiOS04MTZlLTFhZDZmYWRhNTVmMA==",
            model='GigaChat:latest',
            verify_ssl_certs=False,
            profanity_check=False
        )

    def _initialize_embeddings(self):
        model_kwargs = {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': True}
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2", 
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
        except Exception as e:
            print(f"Ошибка при инициализации модели: {e}")
            raise

    def _get_file_hash(self):
        return hashlib.md5(Path(self.file_path).read_bytes()).hexdigest()

    def _load_vector_db(self):
    cache_dir = os.path.join("data", "vector_db_cache")
    index_file = f"{cache_dir}/faiss_index"
    hash_file = f"{cache_dir}/file_hash"

    os.makedirs(cache_dir, exist_ok=True)

    if os.path.exists(index_file) and os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            cached_hash = f.read().strip()
        
        if current_hash == cached_hash:
            self.vector_db = FAISS.load_local(
                folder_path=cache_dir,
                embeddings=self.embeddings,
                index_name="faiss_index"
            )
            print("✓ Загружена кэшированная векторная база")
            return True
    
    print("× Векторная база не загружена")
    return False

    def generate_response(self, query: str) -> str:
        # Поиск и ранжирование документов
        #bm25_retriever = BM25Retriever.from_documents(self.texts)
        #bm25_retriever.k = 20
        faiss_retriever = self.vector_db.as_retriever(search_kwargs={"k": 25})
        
        # Объединение результатов вручную
        #bm25_results = bm25_retriever.get_relevant_documents(query)
        faiss_results = faiss_retriever.get_relevant_documents(query)
        
        # Присваиваем веса и объединяем
        combined_results = []
        #for doc in bm25_results:
        #    combined_results.append((0.4, doc))
        for doc in faiss_results:
            combined_results.append((0.6, doc))
        
        # Сортируем по весу
        combined_results.sort(key=lambda x: x[0], reverse=True)
        result_doc = [doc for _, doc in combined_results]

        # Ранжирование результатов
        #documents = [doc.page_content for doc in result_doc]

        documents = [
                    f"- {doc.page_content} (Ссылка: {doc.metadata.get('Ссылка на видео', 'Нет ссылки')}={doc.metadata.get('time', 'Нет времени')})"
                    for doc in result_doc
                    ]

        pairs = [[query, doc] for doc in documents]
        scores = self.cross_encoder.predict(pairs)
        filtered_pairs = [(score, doc) for score, doc in zip(scores, documents) if score >= 0.01]
        filtered_pairs.sort(key=lambda x: x[0], reverse=True)
        
        if not filtered_pairs:
            return "К сожалению, релевантной информации не найдено."

        # Генерация ответа
        template = '''Роль: Интеллектуальный помощник, отвечающий строго по контексту.

Правила:
 1. Отвечай только на основе контекста. Если информации недостаточно, честно сообщай об этом.
 2. Не придумывай детали. Избегай догадок и обобщений, опирайся только на предоставленные данные.
 3. Формулируй четко и лаконично. Без воды, только суть.
 4. Сохраняй форматирование. Если запрос включает структуру, списки или код, передавай их без искажений.
 5. Используй дружелюбный тон. Общайся просто, понятно и вежливо.
 6. Если контекст не совсем понятен, выдели суть и дай короткий ответ.
 7. Если в контексте представлены ссылки на видео, определи самый релевантный контекст для вопроса пользователя и предоставь только одну ссылку для просмотра видео.

Примеры отклонения запроса:
 • “В предоставленном контексте нет информации для точного ответа.”
 • “На основе имеющихся данных ответить невозможно.”
 • “Чтобы ответить, нужен дополнительный контекст.”

Контекст: {context}
Вопрос: {question}
Ответ:'''
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        context = "\n".join([f"- {doc}" for _, doc in filtered_pairs[:3]])

        return chain.run({'context': context, 'question': query})