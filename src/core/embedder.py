"""
Embedding Generator - Create vector embeddings and FAISS index
"""
import json
import sys
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict
from sentence_transformers import SentenceTransformer
import faiss

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import config
from src.utils.logger import get_logger
from src.utils.metrics import Timer

logger = get_logger("embed_law", config.paths.logs_dir)


class EmbeddingGenerator:
    """Generate embeddings and create FAISS index"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.model.embedding_model
        self.model = None
        self.embedding_dim = None
    
    def load_model(self) -> None:
        """
        Load embedding model
        
        Raises:
            Exception: If model loading fails
        """
        logger.info(f"Loading embedding model: {self.model_name}")
        
        try:
            with Timer() as timer:
                self.model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
            
            logger.info(f"✓ Model loaded in {timer.get_elapsed():.2f}s")
            logger.info(f"  Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.error("Check internet connection or try a different model")
            raise
    
    def load_articles(self) -> Tuple[List[Dict], List[str]]:
        """
        Load articles from metadata and files
        
        Returns:
            Tuple of (metadata, texts)
        
        Raises:
            FileNotFoundError: If metadata not found
        """
        if not config.paths.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata not found: {config.paths.metadata_path}\n"
                "Run split_law.py first!"
            )
        
        logger.info(f"Loading articles from {config.paths.metadata_path}")
        
        try:
            with open(config.paths.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            raise
        
        texts = []
        missing_files = []
        
        for item in metadata:
            file_path = config.paths.base_dir / item['file']
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        texts.append(content)
                        logger.debug(f"Loaded: {item['id']}")
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
                    texts.append("")
                    missing_files.append(item['id'])
            else:
                logger.warning(f"File not found: {file_path}")
                texts.append("")
                missing_files.append(item['id'])
        
        if missing_files:
            logger.warning(f"Missing {len(missing_files)} files: {missing_files[:5]}...")
        
        logger.info(f"✓ Loaded {len(texts)} articles ({len(texts) - len(missing_files)} valid)")
        return metadata, texts
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for texts
        
        Args:
            texts: List of text content
        
        Returns:
            Numpy array of embeddings
        """
        logger.info(f"Creating embeddings for {len(texts)} articles...")
        
        try:
            with Timer() as timer:
                embeddings = self.model.encode(
                    texts,
                    batch_size=config.retrieval.batch_size,
                    show_progress_bar=True,
                    normalize_embeddings=config.retrieval.normalize_embeddings,
                    convert_to_numpy=True
                )
            
            embeddings = embeddings.astype('float32')
            
            logger.info(f"✓ Created embeddings in {timer.get_elapsed():.2f}s")
            logger.info(f"  Shape: {embeddings.shape}")
            logger.info(f"  Memory: {embeddings.nbytes / 1024 / 1024:.2f} MB")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise
    
    def create_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Create FAISS index from embeddings
        
        Args:
            embeddings: Numpy array of embeddings
        
        Returns:
            FAISS index
        """
        logger.info("Creating FAISS index...")
        
        try:
            with Timer() as timer:
                # Use IndexFlatIP for normalized vectors (cosine similarity)
                index = faiss.IndexFlatIP(self.embedding_dim)
                index.add(embeddings)
            
            logger.info(f"✓ Created FAISS index in {timer.get_elapsed():.2f}s")
            logger.info(f"  Total vectors: {index.ntotal}")
            logger.info(f"  Dimension: {index.d}")
            
            return index
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            raise
    
    def save_index(self, index: faiss.Index) -> None:
        """
        Save FAISS index to file
        
        Args:
            index: FAISS index to save
        """
        logger.info(f"Saving FAISS index to {config.paths.faiss_index_path}")
        
        try:
            config.paths.storage_dir.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(config.paths.faiss_index_path))
            
            file_size = config.paths.faiss_index_path.stat().st_size / 1024 / 1024
            logger.info(f"✓ Saved index ({file_size:.2f} MB)")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise
    
    def process(self) -> None:
        """Main processing pipeline"""
        try:
            # Load model
            self.load_model()
            
            # Load articles
            metadata, texts = self.load_articles()
            
            # Validate
            if not texts or all(not t for t in texts):
                raise ValueError("No valid text content found")
            
            # Create embeddings
            embeddings = self.create_embeddings(texts)
            
            # Create FAISS index
            index = self.create_faiss_index(embeddings)
            
            # Save index
            self.save_index(index)
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise


def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info("Embedding Generator - FAISS Index Creation")
        logger.info("=" * 60)
        
        # Initialize generator
        generator = EmbeddingGenerator()
        
        # Process
        with Timer() as timer:
            generator.process()
        
        logger.info("=" * 60)
        logger.info(f"✓ Successfully completed in {timer.get_elapsed():.2f}s")
        logger.info("=" * 60)
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())