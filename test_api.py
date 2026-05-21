"""
Test script for FastAPI endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_search():
    """Test search endpoint"""
    print("\n=== Testing Search ===")
    payload = {
        "query": "quyền của người lao động",
        "top_k": 3,
        "score_threshold": 0.3
    }
    response = requests.post(f"{BASE_URL}/search", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query: {data['query']}")
    print(f"Found: {data['count']} results in {data['retrieval_time']}s")
    for r in data['results']:
        print(f"  - {r['ref']} (score: {r['score']})")


def test_query():
    """Test query endpoint"""
    print("\n=== Testing Query ===")
    payload = {
        "query": "Điều 1 nói về gì?",
        "top_k": 3,
        "score_threshold": 0.3
    }
    response = requests.post(f"{BASE_URL}/query", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Query: {data['query']}")
    print(f"Answer: {data['answer'][:200]}...")
    print(f"Timing: retrieval={data['retrieval_time']}s, llm={data['llm_time']}s, total={data['total_time']}s")
    print(f"Context: {len(data['context'])} articles")


def test_article():
    """Test get article endpoint"""
    print("\n=== Testing Get Article ===")
    response = requests.get(f"{BASE_URL}/article/dieu_001")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"ID: {data['id']}")
    print(f"Title: {data['title']}")
    print(f"Text: {data['text'][:200]}...")


def test_stats():
    """Test stats endpoint"""
    print("\n=== Testing Stats ===")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        print("Testing Law Chatbot RAG API")
        print("=" * 50)
        
        test_health()
        test_search()
        test_query()
        test_article()
        test_stats()
        
        print("\n" + "=" * 50)
        print("✓ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API")
        print("Make sure the API is running: python api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
