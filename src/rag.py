import os
import json
import glob
import hashlib
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import faiss
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
INDEX_DIR = BASE_DIR / "vector_store"
INDEX_FILE = INDEX_DIR / "faiss.index"
META_FILE = INDEX_DIR / "metadata.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHAT_MODEL = "llama-3.3-70b-versatile"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 3

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model (first time downloads ~90MB)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded!")
    return _embedder

def get_embeddings(texts: list[str]) -> np.ndarray:
    """Generate embeddings locally using HuggingFace sentence-transformers."""
    if not texts:
        return np.empty((0, 384), dtype="float32")
    embedder = get_embedder()
    vectors = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    vectors = vectors.astype("float32")
    faiss.normalize_L2(vectors)
    return vectors

def get_groq_client():
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set!\n"
            "1. Go to https://console.groq.com (FREE signup)\n"
            "2. Create API Key\n"
            "3. Add in .env file: GROQ_API_KEY=gsk_your-key-here"
        )
    return Groq(api_key=api_key)

def chunk_text(text: str, chunk_s: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if chunk_s <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_s, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start += chunk_s - overlap
    return chunks

def load_documents() -> list[dict]:
    """Load all markdown files from the knowledge base directory."""
    docs = []
    md_files = glob.glob(str(KNOWLEDGE_BASE_DIR / "*.md"))
    if not md_files:
        raise FileNotFoundError(f"No markdown files found in {KNOWLEDGE_BASE_DIR}")

    for filepath in sorted(md_files):
        path = Path(filepath)
        content = path.read_text(encoding="utf-8")
        filename = path.stem
        chunks = chunk_text(content)

        for i, chunk in enumerate(chunks):
            docs.append({
                "id": hashlib.md5(f"{filename}_{i}_{chunk[:50]}".encode()).hexdigest(),
                "source": filename,
                "chunk_index": i,
                "text": chunk,
            })   
        logger.info(f"Loaded '{filename}' -> {len(chunks)} chunks")

    logger.info(f"Total chunks: {len(docs)}")
    return docs

def build_index(force:bool = False):
    """Build the FAISS index from knowledge base documents."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if INDEX_FILE.exists() and META_FILE.exists() and not force:
        logger.info("Index already exists. Use force=True to rebuild.")
        return
    
    docs = load_documents()
    texts = [d["text"] for d in docs]

    logger.info("Generating embeddings...")

    all_vectors = get_embeddings(texts)
    logger.info(f"Embedded {len(texts)}/{len(texts)} chunks")

    faiss.normalize_L2(all_vectors)
    dim = all_vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(all_vectors)

    faiss.write_index(index, str(INDEX_FILE))
    META_FILE.write_text(json.dumps(docs, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Index built successfully: %s vectors, dimension %s", index.ntotal, dim)


def load_index() -> tuple[faiss.Index, list[dict]]:
    """Load the FAISS index & metadata from disk."""
    if not INDEX_FILE.exists() or not META_FILE.exists():
        raise FileNotFoundError(
            "Vector index not Found. Run 'python src/rag.py --build' to first."
        )
    index = faiss.read_index(str(INDEX_FILE))
    metadata = json.loads(META_FILE.read_text(encoding="utf-8"))
    return index, metadata

def retrieve(query:str, index: faiss.Index, metadata: list[dict], top_k: int = TOP_K) -> list[dict]:
    """Retrieve the most relevant document chunks for a query."""
    query_v = get_embeddings([query])
    faiss.normalize_L2(query_v)
    scores, indices = index.search(query_v, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(metadata):
            doc = metadata[idx].copy()
            doc["score"] = float(score)
            results.append(doc)
    return results

def generate_answer(query: str, context_docs: list[dict]) -> str:
    """Generate an answer using the retrieved context and the LLM."""
    client = get_groq_client()
    context_parts = []
    for i, doc in enumerate(context_docs, 1):
        source = doc["source"].replace("_", " ").title()
        context_parts.append(f"[Source {i}: {source}]\n{doc['text']}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    system_prompt = """You are Hellobooks AI, a friendly and knowledgeable accounting assistant for small and medium businesses. 
You specialize in bookkeeping, financial statements, invoicing, cash flow management, and general accounting concepts.

Answer questions clearly and concisely based on the provided context. 
- Use plain language that non-accountants can understand
- Include relevant formulas or examples where helpful
- If the context doesn't fully cover the question, answer from general accounting knowledge and note this
- Always be accurate and professional
"""

    user_message = f"""Context from knowledge base:
{context}

User Question: {query}

Please provide a clear, helpful answer based on the context above."""

    resp = client.chat.completions.create(
        model = "llama-3.3-70b-versatile",
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature = 0.3,
        max_tokens = 600,
    )
    
    return resp.choices[0].message.content.strip()

def ask(query: str, index: Optional[faiss.Index] = None, metadata: Optional[list] = None) -> dict:
    """
    Full RAG pipeline: retrieve relevant docs → generate answer.
    Returns a dict with answer, sources, and retrieved chunks.
    """
    if index is None or metadata is None:
        index, metadata = load_index()

    retrieved = retrieve(query, index, metadata, top_k=TOP_K)
    answer = generate_answer(query, retrieved)
    sources = sorted({doc["source"] for doc in retrieved})
    return {
        "question": query,
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": retrieved,
    }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hellobooks RAG System")
    parser.add_argument("--build", action="store_true", help="Build/rebuild the vector index")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index exists")
    parser.add_argument("--query", type=str, help="Ask a question")
    args = parser.parse_args()

    if args.build or args.force:
        build_index(force=args.force)
    
    if args.query:
        print(f"\nQuery: {args.query}\n")
        result = ask(args.query)
        print(f"Answer:\n{result['answer']}\n")
        print(f"Sources: {', '.join(result['sources'])}")
    
    if not args.build and not args.force and not args.query:
        parser.print_help()
