import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from rag import ask, build_index, load_index, INDEX_FILE, META_FILE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_idx = None
_metadata = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load vector index at startup."""
    global _idx, _metadata
    logger.info("Starting HelloBooks AI...")

    if not INDEX_FILE.exists() or not META_FILE.exists():
        logger.info("Vector index not found - building now...")
        try:
            build_index()
        except Exception as e:
            logger.error(f"Failed to build index: {e}")
            raise

    _idx, _metadata = load_index()
    logger.info(f"Index loaded: {_idx.ntotal} vectors ready")
    yield
    logger.info("Shutting down HelloBooks AI...")

app = FastAPI(
    title = "Hello-Books AI",
    description = "AI-powered Bookkeeping assistant using RAG",
    version = "1.0.0",
    lifespan = lifespan,
)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Pydantic Models
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="The accounting question to ask")

class SourceChunk(BaseModel):
    source: str
    text: str
    score: float

class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    chunks: list[SourceChunk]

# Routes

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the web UI."""
    return templates.TemplateResponse(request, "index.html")

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "index_loaded": _idx is not None,
        "vectors": _idx.ntotal if  _idx else 0,
    }

@app.post("/ask", response_model=AnswerResponse)
async def ask_question(body: QuestionRequest):
    """Ask an accounting question and get an AI-generated answer."""
    if _idx is None or _metadata is None:
        raise HTTPException(status_code=503, detail="Vector index not loaded yet")
    try:
        result = ask(body.question, index = _idx, metadata = _metadata)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")
    
    chunks = [
        SourceChunk(
            source = c["source"].replace("_", " ").title(),
            text = c["text"][:300] + ("..." if len(c["text"]) > 300 else ""),
            score = round(c["score"], 4),
        )
        for c in result["retrieved_chunks"]
    ]

    return AnswerResponse(
        question = result["question"],
        answer = result["answer"],
        sources = [s.replace("_", " ").title() for s in result["sources"]],
        chunks = chunks,
    )

@app.post("/rebuild-index")
async def rebuild_idx():
    """Rebuild the vector index from the knowledge base."""
    global _idx, _metadata
    try:
        build_index(force=True)
        _idx, _metadata = load_index()
        return {"status": "ok", "message": "Index rebuilt successfully", "vectors": _idx.ntotal}
    except Exception as e:
        logger.exception("Failed to rebuild index")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="localhost", port=8000, reload=False)
