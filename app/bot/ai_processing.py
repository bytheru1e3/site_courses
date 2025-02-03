# File: ai_processing.py
import os
import hashlib
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from sentence_transformers import CrossEncoder
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models.gigachat import GigaChat

class VectorDatabase:
    def __init__(self, file_path: str = 'data/vvodniy_urok.txt'):
        self.file_path = file_path
        self.embeddings = None
        self.vector_db = None
        self.texts = []
        self.cross_encoder = CrossEncoder('DiTy/cross-encoder-russian-msmarco')
        self.llm = self._init_gigachat()
        self._initialize_embeddings()
        self._load_or_create_vector_db()

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
        self.embeddings = HuggingFaceEmbeddings(
            model_name="deepvk/USER-bge-m3",
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )

    def _get_file_hash(self):
        return hashlib.md5(Path(self.file_path).read_bytes()).hexdigest()

    def _load_or_create_vector_db(self):
        cache_dir = os.path.join("data", "vector_db_cache")
        index_file = f"{cache_dir}/faiss_index"
        hash_file = f"{cache_dir}/file_hash"
        meta_file = f"{cache_dir}/meta.json"

        current_hash = self._get_file_hash()
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
                with open(self.file_path, 'r') as f:
                    doc_text = f.read()
                self.texts = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=100,
                    separators=["\n"]
                ).create_documents([doc_text])
                print("✓ Загружена кэшированная векторная база")
                return

        # Создаем новую базу если кэш устарел
        with open(self.file_path, 'r') as f:
            doc_text = f.read()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n"]
        )
        self.texts = text_splitter.create_documents([doc_text])
        self.vector_db = FAISS.from_documents(self.texts, self.embeddings)
        
        # Сохраняем новую версию
        self.vector_db.save_local(
            folder_path=cache_dir,
            index_name="faiss_index"
        )
        with open(hash_file, 'w') as f:
            f.write(current_hash)
        print("✓ Создана новая векторная база")

    def generate_response(self, query: str) -> str:
        # Поиск и ранжирование документов
        bm25_retriever = BM25Retriever.from_documents(self.texts)
        bm25_retriever.k = 10
        faiss_retriever = self.vector_db.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=[0.4, 0.6]
        )
        result_doc = ensemble_retriever.get_relevant_documents(query)

        # Ранжирование результатов
        documents = [doc.page_content for doc in result_doc]
        pairs = [[query, doc] for doc in documents]
        scores = self.cross_encoder.predict(pairs)
        filtered_pairs = [(score, doc) for score, doc in zip(scores, documents) if score >= 0.01]
        filtered_pairs.sort(key=lambda x: x[0], reverse=True)
        
        if not filtered_pairs:
            return "К сожалению, релевантной информации не найдено."

        # Генерация ответа
        template = '''Ответь на вопрос пользователя. \
                    Используй при этом только информацию из контекста. Если в контексте нет \
                    информации для ответа, сообщи об этом пользователю.
                    Контекст: {context}
                    Вопрос: {question}
                    Ответ:'''
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        context = "\n".join([f"- {doc}" for _, doc in filtered_pairs[:3]])
        return chain.run({'context': context, 'question': query})