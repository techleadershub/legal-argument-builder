import os
import json
import glob
import time
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Load env vars for OpenAI API Key
load_dotenv()

# Constants
DATA_DIR = "./data"
QDRANT_PATH = "./qdrant_db"
COLLECTION_NAME = "case_law"
# Using OpenAI text-embedding-3-small which is fast, cheap, and good
# Dimension is 1536
EMBEDDING_MODEL = "text-embedding-3-small" 
VECTOR_SIZE = 1536
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
BATCH_SIZE = 100  # Number of chunks to upsert at once

def ingest_data():
    start_time = time.time()
    print("🚀 Starting ingestion process...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        return

    print("Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    print(f"Initializing Qdrant at {QDRANT_PATH}...")
    client = QdrantClient(path=QDRANT_PATH)
    
    # Check if collection exists and has data
    if client.collection_exists(COLLECTION_NAME):
        try:
            count_result = client.count(COLLECTION_NAME)
            if count_result.count > 0:
                print(f"✅ Collection '{COLLECTION_NAME}' already exists with {count_result.count} documents. Skipping ingestion.")
                return
        except Exception as e:
            print(f"⚠️ Error checking collection count: {e}. Proceeding with fresh ingestion.")
            pass # Fall through to re-ingest if check fails

    # Recreate collection to ensure fresh start and correct dimensions if not existing or empty/error
    if client.collection_exists(COLLECTION_NAME):
        print(f"Removing existing collection '{COLLECTION_NAME}' (empty or forced refresh)...")
        client.delete_collection(COLLECTION_NAME)
        
    print(f"Creating collection '{COLLECTION_NAME}' with size {VECTOR_SIZE}...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    print("📂 Loading documents...")
    documents = []
    
    # Find all txt files
    txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    total_files = len(txt_files)
    print(f"Found {total_files} text files.")
    
    for i, txt_path in enumerate(txt_files):
        try:
            # Read text content
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Read metadata
            base_name = os.path.splitext(txt_path)[0]
            json_path = base_name + "_metadata.json"
            
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Ensure topic is in metadata
            filename = os.path.basename(txt_path)
            topic_from_filename = "_".join(filename.split("_")[:-1])
            
            if "topic" not in metadata:
                metadata["topic"] = topic_from_filename
            
            # Add source to metadata for citation
            metadata["source"] = filename
                
            documents.append(Document(page_content=content, metadata=metadata))
            
            if (i + 1) % 50 == 0:
                print(f"  - Loaded {i + 1}/{total_files} files...")
            
        except Exception as e:
            print(f"❌ Error processing {txt_path}: {e}")

    print(f"✅ Loaded {len(documents)} documents.")

    print(f"✂️ Chunking documents (Size={CHUNK_SIZE}, Overlap={CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    
    chunks = text_splitter.split_documents(documents)
    total_chunks = len(chunks)
    print(f"✅ Created {total_chunks} chunks.")

    print("📥 Indexing chunks into Qdrant in batches...")
    
    # Batch processing
    for i in range(0, total_chunks, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        try:
            vector_store.add_documents(batch)
            progress = min(i + BATCH_SIZE, total_chunks)
            print(f"  - Indexed {progress}/{total_chunks} chunks ({(progress/total_chunks)*100:.1f}%)")
        except Exception as e:
            print(f"❌ Error indexing batch starting at {i}: {e}")
            # Optional: continue or break? Let's continue to try to get as much as possible
            continue

    elapsed = time.time() - start_time
    print(f"🎉 Ingestion complete in {elapsed:.2f} seconds!")

if __name__ == "__main__":
    ingest_data()
