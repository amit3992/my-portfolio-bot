# My Portfolio Chatbot Backend

This is the backend for a personal AI chatbot that lives on [uh-mit.com](https://uh-mit.com). It answers questions about my resume, projects, and experience by using a combination of:

- 🦙 **Mistral via Ollama** (for local dev) (Work in progress)
- 🤖 **OpenAI GPT-4o** (for hosted use)
- 🔍 **FAISS vector store** (for retrieval-augmented generation)
- ⚡ **FastAPI** (for fast, async API serving)

### ✨ Features
- Resume Q&A with RAG (retrieval-augmented generation)
- Dual LLM support (local Ollama / remote OpenAI)
- Embedded chatbot UI on portfolio site
- Easy to run locally with Python

## Features

- PDF resume processing and embedding generation
- RAG implementation using FAISS for efficient retrieval
- Flexible LLM routing (OpenAI/Ollama support)
- FastAPI server with CORS support
- Environment-based configuration

## Prerequisites

- Python 3.12+
- OpenAI API key (for embeddings and optional LLM)
- Ollama (optional, for local LLM support)
- Resume in PDF format

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   make install
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Place your resume at `data/resume.pdf`

5. Initialize the embeddings:
   ```bash
   make setup
   ```

## Usage

1. Start the server:
   ```bash
   make run
   ```

2. The API will be available at `http://localhost:8000`

3. Test the chat endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What are your skills?"}'
   ```

## Development

- Format code: `make format`
- Run linting: `make lint`
- Run tests: `make test`
- Full build: `make build`

## Project Structure

```
.
├── app.py              # FastAPI application
├── rag_engine.py       # RAG implementation
├── llm_router.py       # LLM routing logic
├── load_resume.py      # PDF processing
├── requirements.txt    # Dependencies
└── Makefile           # Build automation
```

## API Documentation

When the server is running, visit:
- OpenAPI docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

See [LICENSE](LICENSE) file.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
