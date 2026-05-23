"""
Law Retriever - Semantic search for law articles
"""
import json
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache
from sentence_transformers import SentenceTransformer
import faiss

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import config
from src.utils.logger import get_logger
from src.utils.metrics import Timer

logger = get_logger("retriever")


class LawRetriever:
    """Semantic search for law articles using FAISS"""
    
    def __init__(self, model_name: str = None):
        """
        Initialize retriever
        
        Args:
            model_name: Embedding model name (optional)
        """
        self.model_name = model_name or config.model.embedding_model
        self.model = None
        self.index = None
        self.metadata = None
        self._content_cache = {}
        
        # Load components
        self._load_model()
        self._load_index()
        self._load_metadata()
        
        logger.info("✓ Retriever initialized successfully")
    
    def _load_model(self) -> None:
        """Load embedding model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("✓ Model loaded")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise Exception(f"Cannot load embedding model: {e}")
    
    def _load_index(self) -> None:
        """Load FAISS index"""
        if not config.paths.faiss_index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {config.paths.faiss_index_path}\n"
                "Run embed_law.py first!"
            )
        
        try:
            logger.info(f"Loading FAISS index from {config.paths.faiss_index_path}")
            self.index = faiss.read_index(str(config.paths.faiss_index_path))
            logger.info(f"✓ Loaded index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise Exception(f"Cannot load FAISS index: {e}")
    
    def _load_metadata(self) -> None:
        """Load metadata"""
        if not config.paths.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata not found: {config.paths.metadata_path}\n"
                "Run split_law.py first!"
            )
        
        try:
            logger.info(f"Loading metadata from {config.paths.metadata_path}")
            with open(config.paths.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            logger.info(f"✓ Loaded metadata for {len(self.metadata)} articles")
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            raise Exception(f"Cannot load metadata: {e}")
    
    def _load_content(self, file_path: str) -> Optional[str]:
        """
        Load article content with caching
        
        Args:
            file_path: Relative path to article file
        
        Returns:
            Article content or None if not found
        """
        # Check cache
        if file_path in self._content_cache:
            return self._content_cache[file_path]
        
        # Load from file
        full_path = config.paths.base_dir / file_path
        
        if not full_path.exists():
            logger.warning(f"File not found: {full_path}")
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Cache content
            self._content_cache[file_path] = content
            return content
            
        except Exception as e:
            logger.error(f"Failed to read {full_path}: {e}")
            return None
    
    def search(
        self,
        query: str,
        k: int = None,
        score_threshold: float = None
    ) -> List[Dict]:
        """
        Search for relevant law articles
        
        Args:
            query: Search query
            k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of search results with ref, text, and score
        """
        k = k or config.retrieval.top_k
        score_threshold = score_threshold or config.retrieval.score_threshold
        
        logger.debug(f"Searching: '{query}' (k={k}, threshold={score_threshold})")
        
        try:
            with Timer() as timer:
                # Encode query
                query_vec = self.model.encode(
                    [query],
                    normalize_embeddings=config.retrieval.normalize_embeddings,
                    convert_to_numpy=True
                ).astype('float32')
                
                # Search FAISS index
                scores, indices = self.index.search(query_vec, k)
            
            logger.debug(f"Search completed in {timer.get_elapsed():.3f}s")
            
            # Process results
            results = []
            for idx, score in zip(indices[0], scores[0]):
                # Validate index
                if idx < 0 or idx >= len(self.metadata):
                    logger.warning(f"Invalid index: {idx}")
                    continue
                
                # Check score threshold
                if score < score_threshold:
                    logger.debug(f"Skipping result with low score: {score:.3f}")
                    continue
                
                # Get metadata
                meta = self.metadata[idx]
                
                # Load content
                content = self._load_content(meta['file'])
                if content is None:
                    continue
                
                results.append({
                    "ref": meta['title'],
                    "text": content,
                    "score": round(float(score), 3),
                    "id": meta['id']
                })
            
            logger.debug(f"Returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """
        Get article by ID
        
        Args:
            article_id: Article ID (e.g., "dieu_001")
        
        Returns:
            Article data or None if not found
        """
        for meta in self.metadata:
            if meta['id'] == article_id:
                content = self._load_content(meta['file'])
                if content:
                    return {
                        "id": meta['id'],
                        "title": meta['title'],
                        "text": content
                    }
        return None
    
    def clear_cache(self) -> None:
        """Clear content cache"""
        self._content_cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict:
        """Get retriever statistics"""
        return {
            "total_articles": len(self.metadata),
            "index_size": self.index.ntotal,
            "cache_size": len(self._content_cache),
            "model": self.model_name
        }