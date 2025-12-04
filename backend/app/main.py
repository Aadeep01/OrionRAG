import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, documents, search, upload
from app.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.gemini_client import GeminiClient
from app.services.vector_store import VectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events"""

    # Startup
    logger.info("Starting Universal Document Intelligence System...")

    try:
        # Initialize Gemini client
        gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
        app.state.gemini_client = gemini_client
        logger.info("✓ Gemini client initialized")

        # Initialize vector store
        vector_store = VectorStore(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            collection_name=settings.QDRANT_COLLECTION_NAME,
        )
        await vector_store.initialize()
        app.state.vector_store = vector_store
        logger.info("✓ Vector store initialized")

        # Initialize document processor
        document_processor = DocumentProcessor(gemini_client)
        app.state.document_processor = document_processor
        logger.info("✓ Document processor initialized")

        logger.info("🚀 System ready!")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e!s}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    if hasattr(app.state, "vector_store"):
        await app.state.vector_store.close()


# Create FastAPI app
app = FastAPI(
    title="Universal Document Intelligence API",
    description="RAG system powered by Gemini 2.5",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])


# Health check
@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint"""
    gemini_status = (
        "connected" if hasattr(app.state, "gemini_client") else "disconnected"
    )
    vector_store_status = (
        "connected" if hasattr(app.state, "vector_store") else "disconnected"
    )

    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "gemini": gemini_status,
            "vector_store": vector_store_status
        },
    }


# Root endpoint
@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint"""
    return {
        "message": "Universal Document Intelligence API",
        "docs": "/docs",
        "health": "/health",
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc!s}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
