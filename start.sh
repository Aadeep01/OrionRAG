#!/bin/bash

# Quick Start Script for Universal Document Intelligence System

set -e

echo "🚀 Universal Document Intelligence System - Quick Start"
echo "========================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your GEMINI_API_KEY"
    echo "   Get your API key from: https://aistudio.google.com/app/apikey"
    exit 1
fi

# Check if GEMINI_API_KEY is set
if grep -q "your_gemini_api_key_here" .env; then
    echo "⚠️  GEMINI_API_KEY not configured in .env"
    echo "   Please edit .env and add your actual API key"
    echo "   Get your API key from: https://aistudio.google.com/app/apikey"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

echo "✅ Prerequisites checked"
echo ""

# Start services
echo "🐳 Starting Docker services..."
cd docker
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo ""
echo "🏥 Checking backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check logs with: docker logs doc-backend"
        exit 1
    fi
    sleep 2
done

echo ""
echo "✅ System is ready!"
echo ""
echo "📚 Available endpoints:"
echo "   - API Docs:  http://localhost:8000/docs"
echo "   - Health:    http://localhost:8000/health"
echo "   - Upload:    POST http://localhost:8000/api/upload/"
echo "   - Search:    POST http://localhost:8000/api/search/"
echo "   - Chat:      POST http://localhost:8000/api/chat/"
echo "   - Documents: GET  http://localhost:8000/api/documents/"
echo ""
echo "🧪 Test the system:"
echo "   curl http://localhost:8000/health"
echo ""
echo "📖 View logs:"
echo "   docker logs -f doc-backend"
echo ""
echo "🛑 Stop services:"
echo "   make down"
echo ""
