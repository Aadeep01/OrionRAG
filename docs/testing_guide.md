# Testing Guide

## Prerequisites
- Docker Desktop running
- Gemini API key configured in `.env`

## Setup

1. **Configure Environment**
```bash
# Copy and edit .env file
cp .env.example .env
# Add your GEMINI_API_KEY
```

2. **Start Services**
```bash
cd docker
docker-compose up -d
```

3. **Check Health**
```bash
curl http://localhost:8000/health
```

## API Testing

### 1. Upload a Document

```bash
curl -X POST "http://localhost:8000/api/upload/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.pdf"
```

Expected response:
```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "original_filename": "document.pdf",
  "file_type": "pdf",
  "file_size": 12345,
  "upload_date": "2025-12-03T...",
  "processed": false,
  "num_chunks": 0,
  ...
}
```

### 2. List Documents

```bash
curl http://localhost:8000/api/documents/
```

### 3. Search Documents

```bash
curl -X POST "http://localhost:8000/api/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic?",
    "limit": 5
  }'
```

### 4. Chat with Documents

```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Summarize the key points"}
    ]
  }'
```

### 5. Delete a Document

```bash
curl -X DELETE "http://localhost:8000/api/documents/{document_id}"
```

## Interactive API Documentation

Visit: http://localhost:8000/docs

This provides a Swagger UI for testing all endpoints interactively.

## Monitoring Logs

```bash
# Backend logs
docker logs -f doc-backend

# Postgres logs
docker logs -f doc-postgres

# Qdrant logs
docker logs -f doc-qdrant
```

## Common Issues

### Issue: Backend fails to start
- Check if Gemini API key is set
- Verify Postgres and Qdrant are healthy
- Check logs: `docker logs doc-backend`

### Issue: Document processing fails
- Check file format is supported
- Verify Gemini API quota
- Check background task logs

### Issue: Search returns no results
- Ensure document is processed (`processed: true`)
- Check if embeddings were generated
- Verify Qdrant collection exists

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v
```
