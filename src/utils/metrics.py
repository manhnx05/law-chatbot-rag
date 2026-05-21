"""
Metrics tracking for Law Chatbot RAG system
"""
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query: str
    timestamp: str
    retrieval_time: float
    llm_time: float
    total_time: float
    num_results: int
    top_score: float
    model_used: str
    success: bool
    error: Optional[str] = None


class MetricsTracker:
    """Track and store system metrics"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self.queries: List[QueryMetrics] = []
        self.stats = defaultdict(int)
        
    def track_query(self, metrics: QueryMetrics):
        """Track a query execution"""
        self.queries.append(metrics)
        self.stats['total_queries'] += 1
        if metrics.success:
            self.stats['successful_queries'] += 1
        else:
            self.stats['failed_queries'] += 1
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        if not self.queries:
            return {
                'total_queries': 0,
                'avg_retrieval_time': 0,
                'avg_llm_time': 0,
                'avg_total_time': 0,
                'success_rate': 0
            }
        
        successful = [q for q in self.queries if q.success]
        
        return {
            'total_queries': len(self.queries),
            'successful_queries': len(successful),
            'failed_queries': len(self.queries) - len(successful),
            'success_rate': len(successful) / len(self.queries) * 100,
            'avg_retrieval_time': sum(q.retrieval_time for q in successful) / len(successful) if successful else 0,
            'avg_llm_time': sum(q.llm_time for q in successful) / len(successful) if successful else 0,
            'avg_total_time': sum(q.total_time for q in successful) / len(successful) if successful else 0,
            'avg_num_results': sum(q.num_results for q in successful) / len(successful) if successful else 0,
            'avg_top_score': sum(q.top_score for q in successful) / len(successful) if successful else 0,
        }
    
    def save(self):
        """Save metrics to file"""
        if not self.storage_path:
            return
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'summary': self.get_summary(),
            'queries': [asdict(q) for q in self.queries]
        }
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self):
        """Load metrics from file"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.queries = [QueryMetrics(**q) for q in data.get('queries', [])]
        self.stats['total_queries'] = len(self.queries)
        self.stats['successful_queries'] = sum(1 for q in self.queries if q.success)
        self.stats['failed_queries'] = len(self.queries) - self.stats['successful_queries']


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self):
        self.start_time = None
        self.elapsed = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
    
    def get_elapsed(self) -> float:
        """Get elapsed time in seconds"""
        return self.elapsed
