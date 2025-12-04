from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_gemini_client, get_vector_store
from app.models.api import SearchQuery, SearchResult
from app.services.gemini_client import GeminiClient
from app.services.vector_store import VectorStore

router = APIRouter()


@router.post("/", response_model=list[SearchResult])
async def search_documents(
    query: SearchQuery,
    vector_store: VectorStore = Depends(get_vector_store),
    gemini_client: GeminiClient = Depends(get_gemini_client),
) -> list[SearchResult]:
    try:
        # 1. Generate query embedding
        query_embedding = await gemini_client.get_query_embedding(query.query)

        # 2. Search in Vector DB
        # Convert filters if necessary (simple implementation for now)
        search_results = await vector_store.search(
            query_vector=query_embedding,
            limit=query.limit,
            filter_conditions=None,  # Implement filter conversion logic if needed
        )

        # 3. Format results
        results = []
        for hit in search_results:
            payload = hit.payload or {}
            results.append(
                SearchResult(
                    document_id=payload.get("document_id"),
                    chunk_id=hit.id,
                    content=payload.get("content"),
                    score=hit.score,
                    metadata=payload.get("metadata"),
                    page_number=payload.get("metadata", {}).get("page_number"),
                    filename=payload.get("metadata", {}).get("source", "Unknown"),
                )
            )

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
