from typing import List, Dict, Any
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from langchain_core.tools import tool

load_dotenv()

# Configuration (should match ingestion)
QDRANT_PATH = "./qdrant_db"
COLLECTION_NAME = "case_law"
EMBEDDING_MODEL = "text-embedding-3-small"

# 1. Initialize Vector Store connection
# We do this globally so it's reused
_embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
_client = QdrantClient(path=QDRANT_PATH)
_vector_store = QdrantVectorStore(
    client=_client,
    collection_name=COLLECTION_NAME,
    embedding=_embeddings,
)

@tool
def keyword_extractor_tool(text: str) -> List[str]:
    """
    Extracts 5-10 search keywords from the given legal text or issue description.
    Useful for refining search queries when the original text is too long or complex.
    """
    # In a real scenario, this might call an LLM. 
    # For now, let's use a simple extraction or a lightweight LLM call to save tokens if we wanted.
    # But the design says "Simple Python function or LLM call". 
    # Let's use a simple stop-word removal and frequency approach if we want to avoid extra LLM calls,
    # OR since we have OpenAI access, we can validly use it. 
    # Let's keep it simple for ReAct demonstration: return a list of "refined" keywords 
    # mostly just splitting important words.
    
    # Simple heuristic implementation for speed/cost:
    ignore = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or", "is", "was", "employee", "employer", "court", "case"}
    words = [w.strip(".,;:?!").lower() for w in text.split()]
    keywords = [w for w in words if w not in ignore and len(w) > 3]
    return list(set(keywords))[:10]

@tool
def rag_search_tool(query: str) -> str:
    """
    Searches the case law database for relevant precedents.
    Returns a string representation of the top results.
    """
    results = _vector_store.similarity_search(query, k=5)
    
    output = []
    for i, res in enumerate(results):
        meta = res.metadata
        output.append(
            f"Result {i+1}:\n"
            f"Case: {meta.get('source', 'Unknown')}\n"
            f"Topic: {meta.get('topic', 'N/A')}\n"
            f"Content: {res.page_content}...\n"
        )
    return "\n".join(output)
