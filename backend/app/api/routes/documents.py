import uuid
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies import get_vector_store
from app.core.database import get_db
from app.models.api import DocumentResponse
from app.models.sql import Document
from app.services.vector_store import VectorStore

router = APIRouter()




@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> Sequence[Document]:
    try:
        stmt = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Document:
    try:
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
) -> dict[str, str]:
    try:
        # Get document
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from Vector DB
        await vector_store.delete_document_vectors(str(document_id))

        # Delete from SQL DB
        await db.delete(document)
        await db.commit()

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
