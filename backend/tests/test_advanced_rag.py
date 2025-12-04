import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.gemini_client import GeminiClient
from app.api.routes.chat import chat_with_documents
from app.models.api import ChatRequest, ChatMessage
from qdrant_client.models import ScoredPoint

# Mock settings
with patch("app.services.gemini_client.settings") as mock_settings:
    mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
    mock_settings.GEMINI_EMBEDDING_MODEL = "text-embedding-004"
    mock_settings.TOP_K_RESULTS = 5
    # Oversampling means we expect limit=10

@pytest.mark.asyncio
async def test_gemini_client_query_generation():
    # Mock the Google GenerativeAI model
    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_model_instance = MockModel.return_value
        
        # Test generate_multi_queries
        mock_model_instance.generate_content.return_value.text = "Query 1\nQuery 2\nQuery 3"
        
        client = GeminiClient(api_key="fake_key")
        queries = await client.generate_multi_queries("Original Query", n=3)
        
        assert len(queries) == 3
        assert queries == ["Query 1", "Query 2", "Query 3"]
        
        # Test generate_step_back_query
        mock_model_instance.generate_content.return_value.text = "Step Back Query"
        
        step_back = await client.generate_step_back_query("Original Query")
        assert step_back == "Step Back Query"

@pytest.mark.asyncio
async def test_chat_with_documents_advanced_rag():
    # Mock dependencies
    mock_vector_store = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Setup mocks
    mock_gemini_client.generate_multi_queries.return_value = ["Var 1", "Var 2"]
    mock_gemini_client.generate_step_back_query.return_value = "Step Back"
    mock_gemini_client.generate_hypothetical_answer.return_value = "Hypothetical Answer"
    mock_gemini_client.get_query_embedding.return_value = [0.1, 0.2, 0.3]
    mock_gemini_client.generate_content.return_value = "Final Answer"
    
    # Mock vector store search results
    # We expect 1 batch search call with 5 queries (Original + 2 Vars + 1 Step Back + 1 HyDE)
    
    import uuid
    doc_id1 = str(uuid.uuid4())
    doc_id2 = str(uuid.uuid4())
    chunk_id1 = str(uuid.uuid4())
    chunk_id2 = str(uuid.uuid4())
    
    hit1 = ScoredPoint(id=chunk_id1, version=1, score=0.9, payload={"document_id": doc_id1, "content": "C1", "metadata": {"source": "S1"}}, vector=None)
    hit2 = ScoredPoint(id=chunk_id2, version=1, score=0.8, payload={"document_id": doc_id2, "content": "C2", "metadata": {"source": "S2"}}, vector=None)
    hit3 = ScoredPoint(id=chunk_id1, version=1, score=0.9, payload={"document_id": doc_id1, "content": "C1", "metadata": {"source": "S1"}}, vector=None) # Duplicate
    
    # search_batch returns a list of lists of hits
    mock_vector_store.search_batch.return_value = [
        [hit1], # Original
        [hit2], # Var 1
        [hit3], # Var 2 (Duplicate of hit1)
        [],     # Step Back
        []      # HyDE
    ]
    
    # Mock re-ranking to return indices 0 and 1 (since we have 2 unique hits)
    mock_gemini_client.rerank_documents.return_value = [(0, 0.95), (1, 0.85)]
    
    # Create request
    request = ChatRequest(messages=[ChatMessage(role="user", content="Complex Question")])
    
    # Run function
    response = await chat_with_documents(
        request=request,
        vector_store=mock_vector_store,
        gemini_client=mock_gemini_client
    )
    
    # Verify
    assert response.response == "Final Answer"
    
    # Verify query generation calls
    mock_gemini_client.generate_multi_queries.assert_called_once_with("Complex Question")
    mock_gemini_client.generate_step_back_query.assert_called_once_with("Complex Question")
    mock_gemini_client.generate_hypothetical_answer.assert_called_once_with("Complex Question")
    
    # Verify batch search call
    mock_vector_store.search_batch.assert_called_once()
    # Check that 5 queries were passed
    call_args = mock_vector_store.search_batch.call_args
    assert len(call_args.kwargs['query_vectors']) == 5
    
    # Verify deduplication in citations (Should be 2 unique hits: 1 and 2)
    assert len(response.citations) == 2
    ids = {str(c.chunk_id) for c in response.citations}
    assert chunk_id1 in ids
    assert chunk_id2 in ids

@pytest.mark.asyncio
async def test_gemini_client_fallback():
    """Test that GeminiClient falls back to original query on API error."""
    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_model_instance = MockModel.return_value
        # Simulate API error
        mock_model_instance.generate_content.side_effect = Exception("API Error")
        
        client = GeminiClient(api_key="fake_key")
        
        # Should return list containing just the original query
        queries = await client.generate_multi_queries("Original Query", n=3)
        assert queries == ["Original Query"]
        
        # Should return None for step-back
        step_back = await client.generate_step_back_query("Original Query")
        assert step_back is None

@pytest.mark.asyncio
async def test_chat_with_documents_fallback_handling():
    """Test that chat endpoint handles the fallback (single query) correctly."""
    mock_vector_store = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    # Simulate fallback behavior: generate_multi_queries returns just the original query
    mock_gemini_client.generate_multi_queries.return_value = ["Query"]
    # Step-back returns None
    mock_gemini_client.generate_step_back_query.return_value = None
    # HyDE returns None
    mock_gemini_client.generate_hypothetical_answer.return_value = None
    
    mock_gemini_client.get_query_embedding.return_value = [0.1]
    mock_gemini_client.generate_content.return_value = "Answer"
    
    mock_vector_store.search_batch.return_value = [[]]
    
    request = ChatRequest(messages=[ChatMessage(role="user", content="Query")])
    
    await chat_with_documents(request, mock_vector_store, mock_gemini_client)
    
    # Verify batch search was called exactly once (for "Query")
    mock_vector_store.search_batch.assert_called_once()
    call_args = mock_vector_store.search_batch.call_args
    assert len(call_args.kwargs['query_vectors']) == 1
    
    # Verify we tried to generate multi-queries
    mock_gemini_client.generate_multi_queries.assert_called_once()

@pytest.mark.asyncio
async def test_empty_search_results():
    """Test handling of no search results."""
    mock_vector_store = AsyncMock()
    mock_gemini_client = AsyncMock()
    
    mock_gemini_client.generate_multi_queries.return_value = ["V1"]
    mock_gemini_client.generate_step_back_query.return_value = None
    mock_gemini_client.generate_hypothetical_answer.return_value = None
    mock_gemini_client.get_query_embedding.return_value = [0.1]
    mock_gemini_client.generate_content.return_value = "I don't know"
    
    # Always return empty list for all queries
    mock_vector_store.search_batch.return_value = [[], []]
    
    request = ChatRequest(messages=[ChatMessage(role="user", content="Query")])
    
    response = await chat_with_documents(request, mock_vector_store, mock_gemini_client)
    
    assert response.citations == []
    # Context should be empty string (or handled gracefully by Gemini prompt)
    mock_gemini_client.generate_content.assert_called_with(prompt="Query", context="")
