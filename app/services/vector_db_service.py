import os
import json
import faiss
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class VectorDBService:
    def __init__(
        self,
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        index_file="app/data/vector_index.faiss",
        documents_file="app/data/documents.json",
    ):
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.embedding_dim = embedding_dim
        self.index_file = index_file
        self.documents_file = documents_file
        
        # Создаем директорию для хранения данных, если её нет
        os.makedirs(os.path.dirname(index_file), exist_ok=True)
        os.makedirs(os.path.dirname(documents_file), exist_ok=True)

        self.index = self._load_index()
        self.documents = self._load_documents()
        logger.info("VectorDB service initialized successfully")

    def process_document(self, file_path, document_text):
        """Обработка документа и сохранение его векторного представления"""
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Получаем эмбеддинг для текста документа
            embedding = self.embedding_model.encode(document_text)
            
            # Добавляем документ в базу
            self.documents.append({
                'path': file_path,
                'text': document_text
            })
            
            # Добавляем эмбеддинг в индекс
            self.index.add(embedding.reshape(1, -1))
            
            # Сохраняем изменения
            self.save()
            
            logger.info(f"Document '{file_path}' successfully processed and added to vector database")
            return embedding.tolist()
        
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise

    def search_similar(self, query, top_k=3):
        """Поиск похожих документов"""
        try:
            query_embedding = self.embedding_model.encode(query).reshape(1, -1)
            distances, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    results.append({
                        'path': doc['path'],
                        'text': doc['text'],
                        'similarity': float(distances[0][i])
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching similar documents: {str(e)}")
            raise

    def save(self):
        """Сохранение индекса и документов"""
        try:
            self._save_index()
            self._save_documents()
            logger.info("Vector database saved successfully")
        except Exception as e:
            logger.error(f"Error saving vector database: {str(e)}")
            raise

    def _load_index(self):
        """Загрузка индекса FAISS"""
        try:
            if os.path.exists(self.index_file):
                logger.info(f"Loading index from file: {self.index_file}")
                return faiss.read_index(self.index_file)
            logger.info("Creating new FAISS index")
            return faiss.IndexFlatL2(self.embedding_dim)
        except Exception as e:
            logger.error(f"Error loading FAISS index: {str(e)}")
            raise

    def _save_index(self):
        """Сохранение индекса FAISS"""
        try:
            faiss.write_index(self.index, self.index_file)
            logger.info(f"Index saved to file: {self.index_file}")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {str(e)}")
            raise

    def _load_documents(self):
        """Загрузка документов"""
        try:
            if os.path.exists(self.documents_file):
                logger.info(f"Loading documents from file: {self.documents_file}")
                with open(self.documents_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            logger.info("Creating new documents storage")
            return []
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise

    def _save_documents(self):
        """Сохранение документов"""
        try:
            with open(self.documents_file, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=4)
            logger.info(f"Documents saved to file: {self.documents_file}")
        except Exception as e:
            logger.error(f"Error saving documents: {str(e)}")
            raise
