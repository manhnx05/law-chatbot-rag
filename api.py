"""
FastAPI REST API for Law Chatbot RAG
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uvicorn

from config import config
from modules.retriever import LawRetriever
from utils.logger import get_logger
from utils.metrics import MetricsTracker, QueryMetrics, Timer
import requests

logger = get_logger("api", config.paths.logs_dir)

# Initialize FastAPI
app = FastAPI(
    title="Law Chatbot RAG API",
    description="REST API for Vietnamese Labor Law Q&A System",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
retriever: Optional[LawRetriever] = None
metrics_tracker: Optional[MetricsTracker] = None


# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    top_k: Optional[int] = Field(5, description="Number of results", ge=1, le=20)
    score_threshold: Optional[float] = Field(0.3, description="Minimum score", ge=0.0, le=1.0)


class SearchResult(BaseModel):
    id: str
    ref: str
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    count: int
    retrieval_time: float


class QueryRequest(BaseModel):
    query: str = Field(..., description="User question", min_length=1, max_length=500)
    top_k: Optional[int] = Field(3, description="Number of context articles", ge=1, le=10)
    score_threshold: Optional[float] = Field(0.3, description="Minimum score", ge=0.0, le=1.0)
    model: Optional[str] = Field(None, description="LLM model name")
    temperature: Optional[float] = Field(0.0, description="Sampling temperature", ge=0.0, le=2.0)


class QueryResponse(BaseModel):
    query: str
    answer: str
    context: List[SearchResult]
    model_used: str
    retrieval_time: float
    llm_time: float
    total_time: float
    success: bool


class ArticleResponse(BaseModel):
    id: str
    title: str
    text: str


class StatsResponse(BaseModel):
    total_articles: int
    index_size: int
    cache_size: int
    model: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float
    avg_retrieval_time: float
    avg_llm_time: float
    avg_total_time: float


class HealthResponse(BaseModel):
    status: str
    retriever: bool
    ollama: bool
    faiss_index: bool
    metadata: bool


# Ollama client
class OllamaClient:
    def __init__(self):
        self.base_url = config.llm.ollama_url
        self.api_url = f"{self.base_url}/api/generate"
    
    def check_connection(self) -> bool:
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, model_name: str, temperature: float = 0.0) -> tuple[str, bool]:
        try:
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": config.llm.num_ctx
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=config.llm.timeout)
            response.raise_for_status()
            return response.json()["response"], True
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return str(e), False


ollama = OllamaClient()


# Startup event
@app.on_event("startup")
async def startup_event():
    global retriever, metrics_tracker
    
    logger.info("Starting Law Chatbot RAG API...")
    
    # Initialize retriever
    try:
        retriever = LawRetriever()
        logger.info("✓ Retriever initialized")
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        raise
    
    # Initialize metrics tracker
    if config.enable_metrics:
        metrics_path = config.paths.logs_dir / "api_metrics.json"
        metrics_tracker = MetricsTracker(metrics_path)
        metrics_tracker.load()
        logger.info("✓ Metrics tracker initialized")
    
    logger.info("✓ API ready")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    if metrics_tracker:
        metrics_tracker.save()
    logger.info("API shutdown")


# Routes
@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "name": "Law Chatbot RAG API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if retriever else "unhealthy",
        retriever=retriever is not None,
        ollama=ollama.check_connection(),
        faiss_index=config.paths.faiss_index_path.exists(),
        metadata=config.paths.metadata_path.exists()
    )


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """
    Search for relevant law articles
    
    - **query**: Search query text
    - **top_k**: Number of results to return (1-20)
    - **score_threshold**: Minimum similarity score (0.0-1.0)
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    try:
        with Timer() as timer:
            results = retriever.search(
                query=request.query,
                k=request.top_k,
                score_threshold=request.score_threshold
            )
        
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    id=r.get("id", ""),
                    ref=r["ref"],
                    text=r["text"],
                    score=r["score"]
                ) for r in results
            ],
            count=len(results),
            retrieval_time=round(timer.get_elapsed(), 3)
        )
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query(request: QueryRequest):
    """
    Ask a question and get AI-generated answer
    
    - **query**: User question
    - **top_k**: Number of context articles (1-10)
    - **score_threshold**: Minimum similarity score (0.0-1.0)
    - **model**: LLM model name (optional, uses default)
    - **temperature**: Sampling temperature (0.0-2.0)
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    if not ollama.check_connection():
        raise HTTPException(status_code=503, detail="Ollama not running")
    
    model_name = request.model or config.model.llm_model
    
    try:
        # Search for context
        with Timer() as retrieval_timer:
            context = retriever.search(
                query=request.query,
                k=request.top_k,
                score_threshold=request.score_threshold
            )
        
        if not context:
            raise HTTPException(status_code=404, detail="No relevant articles found")
        
        # Build prompt
        ctx_str = "\n\n".join([f"{r['ref']}:\n{r['text']}" for r in context])
        prompt = f"""Dựa trên Bộ luật Lao động 2019, trả lời câu hỏi sau:

Câu hỏi: {request.query}

Thông tin liên quan:
{ctx_str}

Trả lời ngắn gọn và trích dẫn điều luật:"""
        
        # Generate answer
        with Timer() as llm_timer:
            answer, success = ollama.generate(prompt, model_name, request.temperature)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {answer}")
        
        # Track metrics
        total_time = retrieval_timer.get_elapsed() + llm_timer.get_elapsed()
        if metrics_tracker:
            metrics = QueryMetrics(
                query=request.query,
                timestamp=datetime.now().isoformat(),
                retrieval_time=retrieval_timer.get_elapsed(),
                llm_time=llm_timer.get_elapsed(),
                total_time=total_time,
                num_results=len(context),
                top_score=context[0]['score'],
                model_used=model_name,
                success=True
            )
            metrics_tracker.track_query(metrics)
            metrics_tracker.save()
        
        return QueryResponse(
            query=request.query,
            answer=answer,
            context=[
                SearchResult(
                    id=r.get("id", ""),
                    ref=r["ref"],
                    text=r["text"],
                    score=r["score"]
                ) for r in context
            ],
            model_used=model_name,
            retrieval_time=round(retrieval_timer.get_elapsed(), 3),
            llm_time=round(llm_timer.get_elapsed(), 3),
            total_time=round(total_time, 3),
            success=True
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/article/{article_id}", response_model=ArticleResponse, tags=["Articles"])
async def get_article(article_id: str):
    """
    Get article by ID
    
    - **article_id**: Article ID (e.g., "dieu_001")
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    article = retriever.get_article_by_id(article_id)
    
    if not article:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found")
    
    return ArticleResponse(**article)


@app.get("/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_stats():
    """Get system statistics"""
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    retriever_stats = retriever.get_stats()
    
    if metrics_tracker:
        metrics_summary = metrics_tracker.get_summary()
    else:
        metrics_summary = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'success_rate': 0,
            'avg_retrieval_time': 0,
            'avg_llm_time': 0,
            'avg_total_time': 0
        }
    
    return StatsResponse(
        total_articles=retriever_stats['total_articles'],
        index_size=retriever_stats['index_size'],
        cache_size=retriever_stats['cache_size'],
        model=retriever_stats['model'],
        total_queries=metrics_summary['total_queries'],
        successful_queries=metrics_summary['successful_queries'],
        failed_queries=metrics_summary['failed_queries'],
        success_rate=metrics_summary['success_rate'],
        avg_retrieval_time=metrics_summary['avg_retrieval_time'],
        avg_llm_time=metrics_summary['avg_llm_time'],
        avg_total_time=metrics_summary['avg_total_time']
    )


@app.post("/cache/clear", tags=["Admin"])
async def clear_cache():
    """Clear retriever cache"""
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    retriever.clear_cache()
    return {"message": "Cache cleared successfully"}


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
