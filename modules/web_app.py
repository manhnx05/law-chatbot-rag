"""
Web Application - Streamlit UI for Law Chatbot RAG
"""
import streamlit as st
import requests
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from utils.logger import get_logger
from utils.metrics import MetricsTracker, QueryMetrics, Timer

logger = get_logger("web_app", config.paths.logs_dir)

class OllamaClient:
    """Client for Ollama LLM API"""
    
    def __init__(self):
        self.base_url = config.llm.ollama_url
        self.api_url = f"{self.base_url}/api/generate"
        self.tags_url = f"{self.base_url}/api/tags"
    
    def check_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = requests.get(self.tags_url, timeout=10)
            if response.status_code == 200:
                return [m["name"] for m in response.json().get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    def check_model_exists(self, model_name: str) -> bool:
        """Check if model exists"""
        available = self.get_available_models()
        return (
            model_name in available or
            f"{model_name}:latest" in available or
            any(name.startswith(model_name + ":") for name in available)
        )
    
    def generate(
        self,
        prompt: str,
        model_name: str,
        temperature: float = None,
        num_ctx: int = None
    ) -> tuple[str, bool]:
        """
        Generate response from LLM
        
        Args:
            prompt: Input prompt
            model_name: Model to use
            temperature: Sampling temperature
            num_ctx: Context window size
        
        Returns:
            Tuple of (response, success)
        """
        if not self.check_connection():
            return "❌ Ollama chưa chạy. Chạy 'ollama serve' trước.", False
        
        if not self.check_model_exists(model_name):
            return f"❌ Model '{model_name}' chưa có. Chạy 'ollama pull {model_name}'", False
        
        try:
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or config.llm.temperature,
                    "num_ctx": num_ctx or config.llm.num_ctx
                }
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=config.llm.timeout
            )
            
            if response.status_code == 500:
                return f"❌ Lỗi server. Thử: ollama pull {model_name} hoặc khởi động lại Ollama", False
            
            response.raise_for_status()
            return response.json()["response"], True
            
        except requests.exceptions.Timeout:
            return "⏱️ Timeout: Model phản hồi quá chậm. Thử model nhẹ hơn.", False
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"❌ Lỗi: {e}", False


# Initialize Ollama client
ollama = OllamaClient()

# Initialize metrics tracker
if config.enable_metrics:
    metrics_path = config.paths.logs_dir / "metrics.json"
    metrics_tracker = MetricsTracker(metrics_path)
    metrics_tracker.load()
else:
    metrics_tracker = None


def build_prompt(query: str, context: List[Dict]) -> str:
    """Build prompt for LLM"""
    ctx_str = "\n\n".join([f"{r['ref']}:\n{r['text']}" for r in context])
    
    return f"""Dựa trên Bộ luật Lao động 2019, trả lời câu hỏi sau:

Câu hỏi: {query}

Thông tin liên quan:
{ctx_str}

Trả lời ngắn gọn và trích dẫn điều luật:"""


def process_query(query: str, retriever, model_name: str) -> tuple[str, List[Dict], QueryMetrics]:
    """
    Process user query
    
    Returns:
        Tuple of (answer, context, metrics)
    """
    # Track retrieval time
    with Timer() as retrieval_timer:
        context = retriever.search(query, k=config.retrieval.top_k)
    
    # Check if context found
    if not context:
        metrics = QueryMetrics(
            query=query,
            timestamp=datetime.now().isoformat(),
            retrieval_time=retrieval_timer.get_elapsed(),
            llm_time=0,
            total_time=retrieval_timer.get_elapsed(),
            num_results=0,
            top_score=0,
            model_used=model_name,
            success=False,
            error="No relevant articles found"
        )
        return "❌ Không tìm thấy quy định phù hợp. Thử câu hỏi khác.", [], metrics
    
    # Build prompt
    prompt = build_prompt(query, context)
    
    # Generate answer
    with Timer() as llm_timer:
        answer, success = ollama.generate(prompt, model_name)
    
    # Create metrics
    total_time = retrieval_timer.get_elapsed() + llm_timer.get_elapsed()
    metrics = QueryMetrics(
        query=query,
        timestamp=datetime.now().isoformat(),
        retrieval_time=retrieval_timer.get_elapsed(),
        llm_time=llm_timer.get_elapsed(),
        total_time=total_time,
        num_results=len(context),
        top_score=context[0]['score'] if context else 0,
        model_used=model_name,
        success=success,
        error=None if success else answer
    )
    
    return answer, context, metrics


# Streamlit UI Configuration
st.set_page_config(
    page_title="Luật Lao Động AI",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("⚙️ Cấu hình")
    
    # Model selection
    available_models = ollama.get_available_models()
    if available_models:
        selected_model = st.selectbox(
            "Chọn Model LLM",
            available_models,
            index=0 if config.model.llm_model not in available_models else available_models.index(config.model.llm_model)
        )
    else:
        selected_model = config.model.llm_model
        st.warning("⚠️ Không tìm thấy model nào")
    
    # Retrieval settings
    st.subheader("Tìm kiếm")
    top_k = st.slider("Số điều luật tham khảo", 1, 10, config.retrieval.top_k)
    score_threshold = st.slider("Ngưỡng độ liên quan", 0.0, 1.0, config.retrieval.score_threshold, 0.05)
    
    # Statistics
    if metrics_tracker:
        st.subheader("📊 Thống kê")
        summary = metrics_tracker.get_summary()
        st.metric("Tổng câu hỏi", summary['total_queries'])
        st.metric("Tỷ lệ thành công", f"{summary['success_rate']:.1f}%")
        if summary['total_queries'] > 0:
            st.metric("Thời gian TB", f"{summary['avg_total_time']:.2f}s")
    
    # System status
    st.subheader("🔧 Trạng thái hệ thống")
    if ollama.check_connection():
        st.success("✓ Ollama đang chạy")
    else:
        st.error("✗ Ollama chưa chạy")
    
    if config.paths.faiss_index_path.exists():
        st.success("✓ FAISS index sẵn sàng")
    else:
        st.error("✗ FAISS index chưa có")


# Main UI
st.title("⚖️ Hỏi Đáp Bộ luật Lao động 2019")
st.caption("Hệ thống RAG chuyên nghiệp - Powered by FAISS & Ollama")

# Check prerequisites
if not config.paths.metadata_path.exists():
    st.error("❌ Chưa chạy: python modules/split_law.py")
    st.stop()

if not config.paths.faiss_index_path.exists():
    st.error("❌ Chưa chạy: python modules/embed_law.py")
    st.stop()

# Load retriever
@st.cache_resource
def load_retriever():
    try:
        from modules.retriever import LawRetriever
        return LawRetriever()
    except Exception as e:
        st.error(f"❌ Lỗi khởi tạo: {e}")
        st.stop()

retriever = load_retriever()

# Check Ollama and find available model
if not ollama.check_connection():
    st.error("❌ Ollama chưa chạy. Chạy: ollama serve")
    st.stop()

current_model = selected_model
if not ollama.check_model_exists(current_model):
    st.warning(f"⚠️ Model {current_model} chưa có, tìm model khác...")
    for fallback in config.model.fallback_models:
        if ollama.check_model_exists(fallback):
            current_model = fallback
            st.info(f"✓ Sử dụng model: {current_model}")
            break
    else:
        st.error("❌ Không tìm thấy model nào. Chạy: ollama pull llama3.2:1b")
        st.stop()

st.success(f"✓ Sẵn sàng với model: {current_model}")

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display context if available
        if msg["role"] == "assistant" and "context" in msg:
            with st.expander("📚 Nguồn tham khảo"):
                for r in msg["context"]:
                    st.caption(f"**{r['ref']}** (Độ liên quan: {r['score']:.2f})")
                    st.write(r['text'][:500] + ("..." if len(r['text']) > 500 else ""))
                    st.divider()

# Chat input
if prompt := st.chat_input("Hỏi về luật lao động..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process query
    with st.chat_message("assistant"):
        with st.spinner("🔍 Đang tìm kiếm và phân tích..."):
            # Override config with UI settings
            config.retrieval.top_k = top_k
            config.retrieval.score_threshold = score_threshold
            
            # Process
            answer, context, query_metrics = process_query(prompt, retriever, current_model)
            
            # Track metrics
            if metrics_tracker:
                metrics_tracker.track_query(query_metrics)
                metrics_tracker.save()
            
            # Display answer
            st.markdown(answer)
            
            # Display context
            if context:
                with st.expander("📚 Nguồn tham khảo"):
                    for r in context:
                        st.caption(f"**{r['ref']}** (Độ liên quan: {r['score']:.2f})")
                        st.write(r['text'][:500] + ("..." if len(r['text']) > 500 else ""))
                        st.divider()
            
            # Display metrics
            if query_metrics.success:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ Tìm kiếm", f"{query_metrics.retrieval_time:.2f}s")
                with col2:
                    st.metric("🤖 LLM", f"{query_metrics.llm_time:.2f}s")
                with col3:
                    st.metric("📊 Tổng", f"{query_metrics.total_time:.2f}s")
    
    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "context": context
    })

# Footer
st.divider()
st.caption("💡 Tip: Hỏi cụ thể về điều luật, quyền lợi, nghĩa vụ để có câu trả lời chính xác nhất")