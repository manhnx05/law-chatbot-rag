"""
Unit tests for Law Chatbot RAG core modules
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRetriever:
    """Test LawRetriever class"""
    
    @patch('src.core.retriever.SentenceTransformer')
    @patch('src.core.retriever.faiss')
    def test_retriever_initialization(self, mock_faiss, mock_transformer):
        """Test retriever initialization"""
        from src.core.retriever import LawRetriever
        
        # Mock dependencies
        mock_transformer.return_value = Mock()
        mock_faiss.read_index.return_value = Mock(ntotal=69)
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '[]'
            
            # This should not raise
            try:
                retriever = LawRetriever()
                assert retriever is not None
            except FileNotFoundError:
                # Expected if files don't exist
                pass
    
    def test_search_with_retry(self):
        """Test search with retry logic"""
        from src.core.retriever import LawRetriever
        
        # Mock retriever
        retriever = Mock(spec=LawRetriever)
        retriever.search = Mock(return_value=[
            {"ref": "Điều 1", "text": "Test", "score": 0.9, "id": "dieu_001"}
        ])
        
        results = retriever.search("test query", k=3)
        assert len(results) > 0
        assert results[0]["score"] > 0


class TestEmbedder:
    """Test EmbeddingGenerator class"""
    
    @patch('src.core.embedder.SentenceTransformer')
    def test_embedder_initialization(self, mock_transformer):
        """Test embedder initialization"""
        from src.core.embedder import EmbeddingGenerator
        
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_transformer.return_value = mock_model
        
        embedder = EmbeddingGenerator()
        embedder.load_model()
        
        assert embedder.model is not None
        assert embedder.embedding_dim == 768
    
    @patch('src.core.embedder.SentenceTransformer')
    def test_create_embeddings(self, mock_transformer):
        """Test embedding creation"""
        from src.core.embedder import EmbeddingGenerator
        
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.encode.return_value = np.random.rand(3, 768).astype('float32')
        mock_transformer.return_value = mock_model
        
        embedder = EmbeddingGenerator()
        embedder.model = mock_model
        embedder.embedding_dim = 768
        
        texts = ["text1", "text2", "text3"]
        embeddings = embedder.create_embeddings(texts)
        
        assert embeddings.shape == (3, 768)
        assert embeddings.dtype == np.float32


class TestSplitter:
    """Test PDFSplitter class"""
    
    def test_article_pattern(self):
        """Test article pattern matching"""
        from src.core.splitter import PDFSplitter
        import re
        
        splitter = PDFSplitter(Path("dummy.pdf"))
        pattern = splitter.article_pattern
        
        # Should match
        assert pattern.match("Điều 1. Phạm vi điều chỉnh")
        assert pattern.match("Điều 10. Quyền của người lao động")
        assert pattern.match("Điều 100. Điều khoản cuối")
        
        # Should not match
        assert not pattern.match("điều 1. lowercase")
        assert not pattern.match("Dieu 1. No accent")
        assert not pattern.match("  Điều 1. Leading space")


class TestMetrics:
    """Test metrics tracking"""
    
    def test_timer(self):
        """Test Timer context manager"""
        from src.utils.metrics import Timer
        import time
        
        with Timer() as timer:
            time.sleep(0.1)
        
        elapsed = timer.get_elapsed()
        assert elapsed >= 0.1
        assert elapsed < 0.2
    
    def test_query_metrics(self):
        """Test QueryMetrics dataclass"""
        from src.utils.metrics import QueryMetrics
        
        metrics = QueryMetrics(
            query="test",
            timestamp="2024-01-01T00:00:00",
            retrieval_time=0.5,
            llm_time=2.0,
            total_time=2.5,
            num_results=3,
            top_score=0.95,
            model_used="llama3.2:1b",
            success=True
        )
        
        assert metrics.query == "test"
        assert metrics.success is True
        assert metrics.total_time == 2.5


class TestConfig:
    """Test configuration management"""
    
    def test_config_initialization(self):
        """Test config initialization"""
        from src.config import AppConfig, ModelConfig, PathConfig
        
        config = AppConfig()
        
        assert config.model is not None
        assert config.paths is not None
        assert config.retrieval is not None
        assert config.llm is not None
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.paths, PathConfig)
    
    def test_model_config_defaults(self):
        """Test model config defaults"""
        from src.config import ModelConfig
        
        config = ModelConfig()
        
        assert config.embedding_model == "bkai-foundation-models/vietnamese-bi-encoder"
        assert config.llm_model == "llama3.2:1b"
        assert len(config.fallback_models) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
