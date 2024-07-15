import unittest
from unittest.mock import MagicMock
from app.services.document_retrieval.document_searcher import DocumentSearcher
from app.services.document_retrieval.embedding_manager import EmbeddingManager

class TestDocumentSearcher(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {'id': '1', 'content': 'This is a test document about AI.'},
            {'id': '2', 'content': 'This document is about machine learning.'},
            {'id': '3', 'content': 'Another document discussing AI and machine learning.'},
            {'id': '4', 'content': 'This is a document about natural language processing.'},
            {'id': '5', 'content': 'Document about deep learning and neural networks.'}
        ]
        self.embedding_manager = MagicMock(spec=EmbeddingManager)
        self.document_searcher = DocumentSearcher(self.documents)
        self.document_searcher.embedding_manager = self.embedding_manager

    def test_generate_document_embeddings(self):
        self.embedding_manager.generate_embedding.side_effect = lambda content: [1.0] * len(content.split())
        document_embeddings = self.document_searcher._generate_document_embeddings()
        self.assertEqual(len(document_embeddings), len(self.documents))
        for doc_embedding in document_embeddings:
            self.assertIn('id', doc_embedding)
            self.assertIn('embedding', doc_embedding)
            self.assertEqual(len(doc_embedding['embedding']), len(self.documents[0]['content'].split()))

    def test_cosine_similarity(self):
        vec1 = [1, 0, 1]
        vec2 = [1, 1, 0]
        similarity = self.document_searcher._cosine_similarity(vec1, vec2)
        expected_similarity = 0.5  # Calculated manually
        self.assertAlmostEqual(similarity, expected_similarity, places=5)

    def test_search_documents(self):
        query = "AI and machine learning"
        self.embedding_manager.generate_embedding.side_effect = lambda content: [1.0] * len(content.split())
        self.document_searcher.document_embeddings = self.document_searcher._generate_document_embeddings()
        results = self.document_searcher.search_documents(query, top_k=3)
        self.assertEqual(len(results), 3)
        self.assertIn('id', results[0])
        self.assertIn('similarity', results[0])
        self.assertGreaterEqual(results[0]['similarity'], results[1]['similarity'])
        self.assertGreaterEqual(results[1]['similarity'], results[2]['similarity'])

if __name__ == '__main__':
    unittest.main()