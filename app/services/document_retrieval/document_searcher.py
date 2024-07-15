from typing import List, Dict, Any
import numpy as np
from app.services.document_retrieval.embedding_manager import EmbeddingManager

class DocumentSearcher:
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.embedding_manager = EmbeddingManager()
        self.document_embeddings = self._generate_document_embeddings()

    def _generate_document_embeddings(self) -> List[Dict[str, Any]]:
        """
        Generate embeddings for all documents.
        """
        document_embeddings = []
        for doc in self.documents:
            embedding = self.embedding_manager.generate_embedding(doc['content'])
            document_embeddings.append({
                'id': doc['id'],
                'embedding': embedding
            })
        return document_embeddings

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate the cosine similarity between two vectors.
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def search_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents that are most similar to the query.
        """
        query_embedding = self.embedding_manager.generate_embedding(query)
        similarities = []
        for doc in self.document_embeddings:
            similarity = self._cosine_similarity(query_embedding, doc['embedding'])
            similarities.append({
                'id': doc['id'],
                'similarity': similarity
            })
        # Sort documents by similarity
        similarities = sorted(similarities, key=lambda x: x['similarity'], reverse=True)
        # Return top_k documents
        return similarities[:top_k]