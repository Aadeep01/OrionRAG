# Quick Commands

## Code Quality

```bash
# Lint code
cd backend && uv run ruff check app/

# Auto-fix issues
cd backend && uv run ruff check app/ --fix

# Format code
cd backend && uv run ruff format app/

# Type check
cd backend && uv run mypy app/
```

## Development

```bash
# Start services
make up

# Stop services
make down

# View logs
make logs

# Test health
make test
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Upload document
curl -X POST "http://localhost:8000/api/upload/" \
  -F "file=@document.pdf"

# Search
curl -X POST "http://localhost:8000/api/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "your query", "limit": 5}'
```
