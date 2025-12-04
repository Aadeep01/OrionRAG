# Component Structure Documentation

This document outlines the component structure and organization for the Universal Document Intelligence System backend.

## Core Components

### 1. **Configuration (`app/config.py`)**
- Centralized settings management using Pydantic
- Environment variable loading
- Type-safe configuration access

### 2. **Database Layer (`app/core/database.py`)**
- Async SQLAlchemy engine setup
- Session management
- Database dependency injection

### 3. **Data Models**

#### SQL Models (`app/models/sql.py`)
- `Document`: Stores document metadata
- `Chunk`: Stores text chunks with references to documents
- `Query`: Analytics/logging for queries

#### API Models (`app/models/api.py`)
- Request/Response Pydantic models
- Data validation
- Serialization

### 4. **Services**

#### Vector Store (`app/services/vector_store.py`)
- Qdrant client wrapper
- Collection initialization
- Vector CRUD operations
- Similarity search

#### Gemini Client (`app/services/gemini_client.py`)
- Google Gemini API integration
- Embedding generation (documents & queries)
- Content generation
- Image OCR capabilities

#### Document Processor (`app/services/document_processor.py`)
- File type detection
- Text extraction (PDF, DOCX, images, etc.)
- Chunking coordination
- Metadata extraction

### 5. **Utilities**

#### Chunking Engine (`app/utils/chunking.py`)
- LangChain text splitters
- Configurable chunk size/overlap
- Smart text splitting

### 6. **API Routes**

#### Upload (`app/api/routes/upload.py`)
- File upload endpoint
- Background processing
- Document ingestion pipeline

#### Search (`app/api/routes/search.py`)
- Semantic search
- Vector similarity matching

#### Chat (`app/api/routes/chat.py`)
- RAG-based chat
- Context retrieval
- Response generation with citations

#### Documents (`app/api/routes/documents.py`)
- List documents
- Get document details
- Delete documents

### 7. **Dependencies (`app/api/dependencies.py`)**
- Service injection
- Shared state management

## Data Flow

### Upload Flow
```
1. User uploads file → upload.py
2. File saved to disk
3. Document record created in PostgreSQL
4. Background task triggered:
   a. DocumentProcessor extracts text
   b. ChunkingEngine splits text
   c. GeminiClient generates embeddings
   d. VectorStore stores vectors in Qdrant
   e. Chunks saved to PostgreSQL
   f. Document marked as processed
```

### Search Flow
```
1. User submits query → search.py
2. GeminiClient generates query embedding
3. VectorStore searches Qdrant
4. Results formatted and returned
```

### Chat Flow
```
1. User sends message → chat.py
2. GeminiClient generates query embedding
3. VectorStore retrieves relevant chunks
4. Context constructed from chunks
5. GeminiClient generates response
6. Response + citations returned
```

## Best Practices

1. **Async/Await**: All I/O operations are async
2. **Dependency Injection**: Services injected via FastAPI dependencies
3. **Error Handling**: Try/catch with proper HTTP exceptions
4. **Type Safety**: Pydantic models for validation
5. **Separation of Concerns**: Clear boundaries between layers
