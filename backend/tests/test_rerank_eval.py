import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.gemini_client import GeminiClient
from app.utils.evaluation import evaluate_rag_response
from app.api.routes.chat import chat_with_documents
from app.models.api import ChatRequest, ChatMessage
from qdrant_client.models import ScoredPoint

# Mock settings
with patch("app.services.gemini_client.settings") as mock_settings:
    mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
    mock_settings.GEMINI_EMBEDDING_MODEL = "text-embedding-004"
    mock_settings.TOP_K_RESULTS = 2

@pytest.mark.asyncio
async def test_rerank_documents():
    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_model_instance = MockModel.return_value
        
        # Mock Gemini response for ranking: Document 2 is best (score 0.9), then Doc 0 (0.8), then Doc 1 (0.1)
        # Input list has 3 docs. Indices: 0, 1, 2.
        # Expected output order: index 2, index 0, index 1.
        mock_model_instance.generate_content.return_value.text = "0.8, 0.1, 0.9"
        
        client = GeminiClient(api_key="fake")
        docs = ["Doc A", "Doc B", "Doc C"]
        
        # Test top_n=3
        ranked = await client.rerank_documents("Query", docs, top_n=3)
        
        assert len(ranked) == 3
        # Check order: (2, 0.9), (0, 0.8), (1, 0.1)
        assert ranked[0][0] == 2
        assert ranked[1][0] == 0
        assert ranked[2][0] == 1
        
        # Test top_n=1
        ranked_top1 = await client.rerank_documents("Query", docs, top_n=1)
        assert len(ranked_top1) == 1
        assert ranked_top1[0][0] == 2

@pytest.mark.asyncio
async def test_evaluate_rag_response():
    mock_client = AsyncMock()
    
    # Mock responses for Faithfulness (0.9) and Relevance (0.8)
    mock_client.generate_content.side_effect = ["0.9", "0.8"]
    
    result = await evaluate_rag_response("Query", "Answer", "Context", mock_client)
    
    assert result["faithfulness"] == 0.9
    assert result["relevance"] == 0.8
    assert mock_client.generate_content.call_count == 2

@pytest.mark.asyncio
async def test_chat_with_reranking():
    mock_vector_store = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Setup mocks
    mock_gemini_client.generate_multi_queries.return_value = []
    mock_gemini_client.generate_step_back_query.return_value = None
    mock_gemini_client.get_query_embedding.return_value = [0.1]
    mock_gemini_client.generate_content.return_value = "Final Answer"
    
    # Mock reranking: Swap order of hits
    # Input hits: [Hit A, Hit B]
    # Rerank returns: [(1, 0.9), (0, 0.5)] -> Hit B is better
    mock_gemini_client.rerank_documents.return_value = [(1, 0.9), (0, 0.5)]
    
    import uuid
    doc_id = str(uuid.uuid4())
    
    hitA = ScoredPoint(id=str(uuid.uuid4()), version=1, score=0.8, payload={"document_id": doc_id, "content": "Content A"}, vector=None)
    hitB = ScoredPoint(id=str(uuid.uuid4()), version=1, score=0.7, payload={"document_id": doc_id, "content": "Content B"}, vector=None)
    
    # Mock search_batch return value (list of lists of hits)
    # Since we have 1 query (multi_queries=[], step_back=None), we expect 1 list of hits
    mock_vector_store.search_batch.return_value = [[hitA, hitB]]
    
    request = ChatRequest(messages=[ChatMessage(role="user", content="Query")])
    
    response = await chat_with_documents(request, mock_vector_store, mock_gemini_client)
    
    # Verify reranking was called
    mock_gemini_client.rerank_documents.assert_called_once()
    
    # Verify citations order: Hit B should be first because it was ranked higher (index 1)
    assert response.citations[0].content == "Content B"
    assert response.citations[1].content == "Content A"
