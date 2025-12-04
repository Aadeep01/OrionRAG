<div align="center">

# Universal Document Intelligence System

### *A RAG system powered by Google Gemini 2.5*

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

</div>

---

## Features

<table>
<tr>
<td width="50%">

**Semantic Search**  
Find information across all documents

**Multi-format Support**  
PDF, DOCX, TXT, Images (OCR)

</td>
<td width="50%">

**AI Chat Interface**  
Ask questions with citations

**Advanced RAG**  
Multi-Query, Step-Back, HyDE

</td>
</tr>
</table>

---

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌─────────────────────────────────┐   │
│  │  Upload → Process → Chunk       │   │
│  │  Embed → Store → Search         │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
         ↓                    ↓
┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │     Qdrant      │
│   (Metadata)    │  │   (Vectors)     │
└─────────────────┘  └─────────────────┘
         ↓
┌─────────────────────────────────────────┐
│        Google Gemini 2.5 API            │
│  • Embeddings (text-embedding-004)      │
│  • Generation (gemini-2.5-flash)        │
│  • OCR (native multimodal)              │
└─────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker Desktop
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Installation

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 2. Start services
make up

# 3. Verify
curl http://localhost:8000/health

# 4. Access API docs
open http://localhost:8000/docs
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/` | Upload documents |
| `POST` | `/api/search/` | Semantic search |
| `POST` | `/api/chat/` | Chat with documents |
| `GET` | `/api/documents/` | List all documents |
| `DELETE` | `/api/documents/{id}` | Delete document |

### Example Usage

```bash
# Upload a document
curl -X POST "http://localhost:8000/api/upload/" -F "file=@sample.pdf"

# Search
curl -X POST "http://localhost:8000/api/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "your search query", "limit": 5}'

# Chat
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is this about?"}]}'
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI (Python 3.11+) |
| **Vector DB** | Qdrant |
| **SQL DB** | PostgreSQL |
| **LLM** | Google Gemini 2.5 Flash |
| **Embeddings** | text-embedding-004 (768D) |
| **Package Manager** | uv |
| **Deployment** | Docker Compose |

---

## Key Features

### Document Processing Pipeline

```
Upload → Extract Text → Chunk → Embed → Store in Vector DB
```

### RAG Pipeline

```
Query → Embed → Search → Re-rank → Generate Answer → Citations
```

**Advanced Techniques:**
- Multi-Query Retrieval
- Step-Back Prompting
- HyDE (Hypothetical Document Embeddings)
- RAG-Fusion
- Batch Processing & HNSW Optimization

---

## Documentation

- [Component Structure](docs/component_structure.md) - Backend architecture
- [Testing Guide](docs/testing_guide.md) - How to test the API
- [Code Quality](docs/code_quality.md) - Ruff & mypy standards
- [Advanced RAG Techniques](docs/advanced_rag_techniques.md) - Deep dive

---

## Development

```bash
make help      # Show available commands
make up        # Start services
make down      # Stop services
make logs      # View all logs
make test      # Test health endpoint
make clean     # Remove all data
```

---

## Why This Stack?

| Technology | Reason |
|------------|--------|
| **Gemini 2.5** | Native multimodal, 1M token context, cost-effective |
| **Qdrant** | Fast vector search, Docker-ready |
| **PostgreSQL** | Reliable metadata storage |
| **FastAPI** | Modern, async, auto-docs |
| **Docker** | Consistent environments |

---