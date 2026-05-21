"""
Configuration management for Law Chatbot RAG system
"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Model configuration"""
    embedding_model: str = "bkai-foundation-models/vietnamese-bi-encoder"
    llm_model: str = "llama3.2:1b"
    fallback_models: list = None
    
    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = [
                "qwen2:0.5b",
                "qwen2:1.5b", 
                "gemma2:2b",
                "llama3.2:3b",
                "phi3:mini",
                "phi3:latest"
            ]


@dataclass
class PathConfig:
    """Path configuration"""
    base_dir: Path = Path(__file__).parent
    data_dir: Path = None
    storage_dir: Path = None
    articles_dir: Path = None
    
    def __post_init__(self):
        self.data_dir = self.base_dir / "data"
        self.storage_dir = self.base_dir / "storage"
        self.articles_dir = self.storage_dir / "articles"
        
        # Create directories if not exist
        self.data_dir.mkdir(exist_ok=True)
        self.storage_dir.mkdir(exist_ok=True)
        self.articles_dir.mkdir(exist_ok=True)
    
    @property
    def pdf_path(self) -> Path:
        return self.data_dir / "luat_lao_dong.pdf"
    
    @property
    def faiss_index_path(self) -> Path:
        return self.storage_dir / "law_index.faiss"
    
    @property
    def metadata_path(self) -> Path:
        return self.storage_dir / "law_metadata.json"
    
    @property
    def logs_dir(self) -> Path:
        logs = self.base_dir / "logs"
        logs.mkdir(exist_ok=True)
        return logs


@dataclass
class RetrievalConfig:
    """Retrieval configuration"""
    top_k: int = 5
    score_threshold: float = 0.3
    batch_size: int = 8
    normalize_embeddings: bool = True


@dataclass
class LLMConfig:
    """LLM configuration"""
    ollama_url: str = "http://localhost:11434"
    temperature: float = 0.0
    num_ctx: int = 4096
    timeout: int = 180
    max_retries: int = 3


@dataclass
class AppConfig:
    """Main application configuration"""
    model: ModelConfig = None
    paths: PathConfig = None
    retrieval: RetrievalConfig = None
    llm: LLMConfig = None
    
    # Logging
    log_level: str = "INFO"
    enable_metrics: bool = True
    
    def __post_init__(self):
        if self.model is None:
            self.model = ModelConfig()
        if self.paths is None:
            self.paths = PathConfig()
        if self.retrieval is None:
            self.retrieval = RetrievalConfig()
        if self.llm is None:
            self.llm = LLMConfig()
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables"""
        config = cls()
        
        # Override from environment
        if os.getenv("EMBEDDING_MODEL"):
            config.model.embedding_model = os.getenv("EMBEDDING_MODEL")
        if os.getenv("LLM_MODEL"):
            config.model.llm_model = os.getenv("LLM_MODEL")
        if os.getenv("OLLAMA_URL"):
            config.llm.ollama_url = os.getenv("OLLAMA_URL")
        if os.getenv("LOG_LEVEL"):
            config.log_level = os.getenv("LOG_LEVEL")
        
        return config


# Global config instance
config = AppConfig.from_env()
