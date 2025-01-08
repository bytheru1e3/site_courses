import numpy as np
import faiss
import json
from app.models import Material
import logging

logger = logging.getLogger(__name__)

class VectorSearch:
    def __init__(self):
        self.dimension = 768  # Размерность векторов
        self.index = None
        self.initialize_index()

    def initialize_index(self):
        """Инициализация индекса FAISS"""
        try:
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info("FAISS index initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing FAISS index: {e}")
            raise

    def create_embedding(self, text):
        """
        Создание векторного представления текста
        Здесь можно использовать любую модель для создания эмбеддингов
        """
        # Заглушка - возвращаем случайный вектор
        vector = np.random.rand(self.dimension).astype('float32')
        return vector.tolist()

    def add_to_index(self, material_id, vector):
        """Добавление вектора в индекс"""
        try:
            vector_np = np.array([vector]).astype('float32')
            self.index.add(vector_np)
            logger.info(f"Vector added to index for material {material_id}")
        except Exception as e:
            logger.error(f"Error adding vector to index: {e}")
            raise

    def search(self, query, k=5):
        """Поиск похожих материалов"""
        try:
            query_vector = self.create_embedding(query)
            query_vector_np = np.array([query_vector]).astype('float32')
            
            D, I = self.index.search(query_vector_np, k)
            
            results = []
            materials = Material.query.all()
            
            for idx in I[0]:
                if idx < len(materials):
                    material = materials[idx]
                    results.append({
                        'id': material.id,
                        'title': material.title,
                        'content': material.content
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            return []

    def rebuild_index(self):
        """Перестроение индекса из базы данных"""
        try:
            self.initialize_index()
            materials = Material.query.all()
            
            for material in materials:
                vector = material.get_vector()
                if vector:
                    self.add_to_index(material.id, vector)
            
            logger.info("Index rebuilt successfully")
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            raise
