import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from qdrant_client.models import PointStruct
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_document_processor,
    get_gemini_client,
    get_vector_store,
)
from app.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.models.api import DocumentResponse
from app.models.sql import Chunk, Document
from app.services.document_processor import DocumentProcessor
from app.services.gemini_client import GeminiClient
from app.services.vector_store import VectorStore
from app.utils.validators import (
    ValidationError,
    validate_file_size,
    validate_upload_file,
)

logger = logging.getLogger(__name__)
router = APIRouter()



async def process_document_background(
    document_id: uuid.UUID,
    file_path: str,
    filename: str,
    content_type: str,
    vector_store: VectorStore,
    gemini_client: GeminiClient,
    document_processor: DocumentProcessor,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            # Create a mock file object or modify processor to take path + metadata
            # For now, let's create a simple object that mimics UploadFile
            class MockFile(UploadFile):
                def __init__(self, filename: str, content_type: str) -> None:
                    self.filename = filename
                    self.content_type = content_type

            mock_file = MockFile(filename, content_type)

            # 1. Process file to get chunks
            chunks_data = await document_processor.process_file(mock_file, file_path)

            # 2. Generate embeddings and prepare vectors
            points = []
            db_chunks = []

            for chunk in chunks_data:
                # Generate embedding
                embedding = await gemini_client.get_embeddings(chunk["content"])

                chunk_id = uuid.uuid4()
                vector_id = str(chunk_id)

                # Create Qdrant point
                points.append(
                    PointStruct(
                        id=vector_id,
                        vector=embedding,
                        payload={
                            "document_id": str(document_id),
                            "content": chunk["content"],
                            "metadata": chunk["metadata"],
                            "chunk_index": chunk["chunk_index"],
                        },
                    )
                )

                # Create DB chunk
                db_chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=chunk["chunk_index"],
                        content=chunk["content"],
                        metadata_=chunk["metadata"],
                        vector_id=vector_id,
                    )
                )

            # 3. Store in Vector DB
            if points:
                await vector_store.upsert_vectors(points)

            # 4. Store in SQL DB
            db.add_all(db_chunks)

            # 5. Update document status
            stmt = select(Document).where(Document.id == document_id)
            result = await db.execute(stmt)
            document = result.scalar_one()

            document.processed = True  # type: ignore[assignment]
            document.num_chunks = len(chunks_data)  # type: ignore[assignment]

            await db.commit()

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e!s}")
            # Update document status to failed
            try:
                stmt = select(Document).where(Document.id == document_id)
                result = await db.execute(stmt)
                document = result.scalar_one()
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to update document status: {e}")

        finally:
            # Cleanup uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)


@router.post("/", response_model=DocumentResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
    gemini_client: GeminiClient = Depends(get_gemini_client),
    document_processor: DocumentProcessor = Depends(get_document_processor),
) -> DocumentResponse:
    """Upload a document for processing.

    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded file
        db: Database session
        vector_store: Vector store instance
        gemini_client: Gemini client instance
        document_processor: Document processor instance

    Returns:
        Document metadata

    Raises:
        ValidationError: If file validation fails
        HTTPException: If upload fails
    """
    # Comprehensive file validation
    safe_filename, ext = validate_upload_file(file)

    # Create upload directory if not exists
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file temporarily
    file_id = uuid.uuid4()
    file_path = upload_dir / f"{file_id}.{ext}"

    try:
        # Save file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Validate file size after saving
        file_size = file_path.stat().st_size
        validate_file_size(file_size)

        # Create document record
        document = Document(
            id=file_id,
            filename=safe_filename,
            original_filename=file.filename or "unknown",
            file_type=ext,
            file_size=file_size,
            processed=False,
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Trigger background processing
        background_tasks.add_task(
            process_document_background,
            uuid.UUID(str(document.id)),
            str(file_path),
            safe_filename,
            file.content_type or "application/octet-stream",
            vector_store,
            gemini_client,
            document_processor,
        )

        return DocumentResponse.model_validate(document)

    except ValidationError:
        # Validation errors are already HTTPExceptions
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file") from e
