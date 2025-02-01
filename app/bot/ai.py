import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import faiss


class VectorDatabase:
    def __init__(self, model_name='all-MiniLM-L6-v2', index_file='vector_index.faiss', metadata_file='metadata.json'):
        self.model = SentenceTransformer(model_name)
        self.index_file = index_file
        self.metadata_file = metadata_file
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = self._load_index()
        self.metadata = self._load_metadata()

    def _load_index(self):
        if os.path.exists(self.index_file):
            index = faiss.read_index(self.index_file)
        else:
            index = faiss.IndexFlatL2(self.dimension)
        return index

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def add_text(self, text, metadata):
        embedding = self.model.encode([text])[0]
        self.index.add(np.array([embedding]))
        idx = len(self.metadata)
        self.metadata[idx] = metadata
        self._save_index()
        self._save_metadata()

    def _save_index(self):
        faiss.write_index(self.index, self.index_file)

    def _save_metadata(self):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=4)

    def search(self, query, top_k=5):
        query_embedding = self.model.encode([query])[0].reshape(1, -1)
        distances, indices = self.index.search(query_embedding, top_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and str(idx) in self.metadata:
                results.append((self.metadata[str(idx)], distances[0][i]))
        return results

    def generate_response(self, query, top_k=5):
        results = self.search(query, top_k)
        response = "\n".join([f"{item[0]} (similarity: {1 - item[1]:.2f})" for item in results])
        return response or "No relevant information found."


# Пример использования
if __name__ == "__main__":
    db = VectorDatabase()
    db.add_text("Пример текста", {"source": "file1.txt"})
    query = "Пример запроса"
    print(db.generate_response(query))
