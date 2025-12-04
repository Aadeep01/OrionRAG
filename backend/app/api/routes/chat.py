import time

from fastapi import APIRouter, Depends, HTTPException
from qdrant_client.models import ScoredPoint

from app.api.dependencies import get_gemini_client, get_vector_store
from app.config import settings
from app.models.api import ChatRequest, ChatResponse, SearchResult
from app.services.gemini_client import GeminiClient
from app.services.vector_store import VectorStore

router = APIRouter()


async def _generate_expanded_queries(
    user_query: str, gemini_client: GeminiClient
) -> list[str]:
    """Generate multiple query variations (Multi-query, Step-back, HyDE)."""
    queries = [user_query]

    # Multi-queries
    multi_queries = await gemini_client.generate_multi_queries(user_query)
    queries.extend(multi_queries)

    # Step-back query
    step_back_query = await gemini_client.generate_step_back_query(user_query)
    if step_back_query:
        queries.append(step_back_query)

    # HyDE
    hypothetical_answer = await gemini_client.generate_hypothetical_answer(user_query)
    if hypothetical_answer:
        queries.append(hypothetical_answer)

    # Deduplicate while preserving order
    return list(dict.fromkeys(queries))


async def _perform_search_and_fusion(
    queries: list[str],
    gemini_client: GeminiClient,
    vector_store: VectorStore,
    top_k: int,
) -> list[ScoredPoint]:
    """Perform batch search and apply RAG-Fusion (RRF)."""
    # Generate embeddings
    query_embeddings = []
    for query in queries:
        emb = await gemini_client.get_query_embedding(query)
        query_embeddings.append(emb)

    # Batch Search (Oversampling)
    batch_results = await vector_store.search_batch(
        query_vectors=query_embeddings, limit=top_k * 2
    )

    # RAG-Fusion: Reciprocal Rank Fusion (RRF)
    rrf_k = 60
    doc_scores: dict[str, float] = {}
    doc_objects: dict[str, ScoredPoint] = {}

    for _, hits in enumerate(batch_results):
        for rank, hit in enumerate(hits):
            hit_id = str(hit.id)
            if hit_id not in doc_objects:
                doc_objects[hit_id] = hit
                doc_scores[hit_id] = 0.0

            doc_scores[hit_id] += 1.0 / (rrf_k + rank + 1)

    # Sort by RRF score descending
    sorted_doc_ids = sorted(
        doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True
    )

    # Return top K unique documents (still oversampled for re-ranking)
    return [doc_objects[doc_id] for doc_id in sorted_doc_ids[: top_k * 2]]


async def _rerank_results(
    user_query: str,
    hits: list[ScoredPoint],
    gemini_client: GeminiClient,
    top_k: int,
) -> list[ScoredPoint]:
    """Rerank search results using Gemini."""
    docs_to_rerank = [
        hit.payload.get("content", "") for hit in hits if hit.payload
    ]

    if not docs_to_rerank:
        return []

    # Call Gemini to rerank
    ranked_indices = await gemini_client.rerank_documents(
        query=user_query, documents=docs_to_rerank, top_n=top_k
    )

    # Select top hits based on ranking
    final_hits = []
    for idx, score in ranked_indices:
        if idx < len(hits):
            hit = hits[idx]
            # Update score with re-ranking score
            hit.score = score
            final_hits.append(hit)

    return final_hits

@router.post("/", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatRequest,
    vector_store: VectorStore = Depends(get_vector_store),
    gemini_client: GeminiClient = Depends(get_gemini_client),
) -> ChatResponse:
    start_time = time.time()
    try:
        # Get the last user message
        user_query = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), None
        )
        if not user_query:
            raise HTTPException(status_code=400, detail="No user message found")

        # 1. Advanced RAG: Query Generation
        unique_queries = await _generate_expanded_queries(user_query, gemini_client)
        print(f"Generated queries: {unique_queries}")

        # 2. Search for relevant context (Multi-Query Search + RAG-Fusion)
        all_hits = await _perform_search_and_fusion(
            unique_queries, gemini_client, vector_store, settings.TOP_K_RESULTS
        )

        # 3. Re-ranking
        final_hits = await _rerank_results(
            user_query, all_hits, gemini_client, settings.TOP_K_RESULTS
        )

        # 4. Construct context and citations
        context_parts = []
        citations = []

        for hit in final_hits:
            payload = hit.payload or {}
            content = payload.get("content")
            source = payload.get("metadata", {}).get("source", "Unknown")

            context_parts.append(f"Source: {source}\nContent: {content}")

            citations.append(
                SearchResult(
                    document_id=payload.get("document_id"),
                    chunk_id=hit.id,
                    content=content,
                    score=hit.score,
                    metadata=payload.get("metadata"),
                    filename=source,
                )
            )

        context = "\n\n".join(context_parts)

        # 5. Generate response using Gemini
        response_text = await gemini_client.generate_content(
            prompt=user_query, context=context
        )

        processing_time = int((time.time() - start_time) * 1000)

        return ChatResponse(
            response=response_text,
            citations=citations,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
