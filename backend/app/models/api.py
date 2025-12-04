from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# --- Document Models ---


class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    metadata_: dict[str, Any] | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: UUID
    upload_date: datetime
    processed: bool
    num_chunks: int
    created_at: datetime
    updated_at: datetime
    metadata_: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Chunk Models ---


class ChunkBase(BaseModel):
    chunk_index: int
    content: str
    page_number: int | None = None
    metadata: dict[str, Any] | None = None


class ChunkCreate(ChunkBase):
    document_id: UUID
    vector_id: str | None = None


class ChunkResponse(ChunkBase):
    id: UUID
    document_id: UUID
    vector_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Search/Chat Models ---


class SearchQuery(BaseModel):
    query: str
    limit: int = 5
    filters: dict[str, Any] | None = None


class SearchResult(BaseModel):
    document_id: UUID
    chunk_id: UUID
    content: str
    score: float
    metadata: dict[str, Any] | None = None
    page_number: int | None = None
    filename: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context_filter: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    citations: list[SearchResult]
    processing_time_ms: int
