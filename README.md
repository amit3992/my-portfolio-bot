# Veda — Portfolio AI Chatbot

Veda is the AI assistant that lives on [uh-mit.com](https://uh-mit.com). It answers questions about Amit's resume, projects, and experience using retrieval-augmented generation (RAG) with streaming responses.

**"Veda"** comes from Sanskrit, meaning *knowledge*.

## Tech Stack

- **LLMs**: Google Gemini 2.0 Flash (primary) with Claude Sonnet fallback
- **Embeddings**: Google `gemini-embedding-001`
- **Vector Store**: FAISS for fast similarity search
- **Backend**: FastAPI with SSE streaming
- **Storage**: Cloudflare R2 (resume PDF) + Supabase Postgres (analytics & knowledge base)
- **Deployment**: Railway with Nixpacks

## Features

- **RAG Pipeline** — PDF resume is embedded and retrieved for context-aware answers
- **Streaming Responses** — Real-time token streaming via Server-Sent Events
- **Conversation Memory** — Maintains chat history within a session for natural follow-ups
- **LLM Fallback** — Automatic failover from Gemini to Claude if the primary provider errors
- **Analytics Dashboard** — Private admin dashboard tracking questions, visitors, sessions, errors, latency, and LLM provider usage
- **Live Knowledge Base** — Add context snippets from the admin dashboard without redeploying
- **IP Geolocation** — Visitor location tracking via ip-api.com
- **Rate Limiting** — 5 requests/minute per IP

## Architecture

```
Resume PDF (R2) → Embeddings (Gemini) → FAISS Index
                                            ↓
User Question → RAG Retrieval → Context + Knowledge Snippets → LLM → Streamed Response
                                                                        ↓
                                                              Analytics (Supabase)
```

## Project Structure

```
├── app.py              # FastAPI app, routes, lifespan
├── rag_engine.py       # PDF loading, embedding, FAISS retrieval
├── llm_router.py       # LLM routing, streaming, fallback logic
├── database.py         # Supabase connection, analytics logging, knowledge CRUD
├── dashboard.py        # Admin dashboard (server-rendered HTML)
├── load_resume.py      # Resume PDF processing
├── requirements.txt    # Python dependencies
├── railway.toml        # Railway deployment config
├── Procfile            # Process entrypoint
└── Makefile            # Dev automation
```

## Setup

### Prerequisites

- Python 3.12+
- Google AI API key (Gemini)
- Anthropic API key (Claude, for fallback)
- Cloudflare R2 bucket with resume PDF
- Supabase project (for analytics + knowledge base)

### Installation

```bash
make install
cp .env.example .env
# Edit .env with your API keys and config
```

### Environment Variables

| Variable | Description |
|---|---|
| `API_KEY` | API key for chat endpoints |
| `GOOGLE_API_KEY` | Google AI / Gemini API key |
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback) |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key |
| `R2_BUCKET_NAME` | R2 bucket name |
| `R2_RESUME_KEY` | Resume PDF filename in R2 |
| `DATABASE_URL` | Supabase Postgres connection string (pooler) |
| `ADMIN_TOKEN` | Token for accessing the admin dashboard |

### Run Locally

```bash
make run
# Available at http://localhost:8000
```

## License

See [LICENSE](LICENSE) file.
