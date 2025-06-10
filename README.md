# My Portfolio Chatbot Backend

A FastAPI-based backend service that provides a conversational interface to interact with my portfolio content using RAG (Retrieval Augmented Generation) and LLM integration.

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
