from typing import cast

from fastapi import Request

from app.services.document_processor import DocumentProcessor
from app.services.gemini_client import GeminiClient
from app.services.vector_store import VectorStore


def get_vector_store(request: Request) -> VectorStore:
    return cast(VectorStore, request.app.state.vector_store)


def get_gemini_client(request: Request) -> GeminiClient:
    return cast(GeminiClient, request.app.state.gemini_client)


def get_document_processor(request: Request) -> DocumentProcessor:
    return cast(DocumentProcessor, request.app.state.document_processor)
