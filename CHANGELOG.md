# Changelog

## Unreleased

### Self-healing database connection
- The Postgres pool now reconnects lazily via `ensure_pool()` instead of being built
  once at startup — so the app recovers automatically after the DB is unreachable at
  boot (e.g. Supabase free-tier auto-pause) without a manual redeploy
- Reconnect attempts are lock-guarded and throttled (30s) so a down DB isn't hammered
- Failed queries drop the pool (`reset_pool()`) so a stale/dead pool self-heals
- Dashboard shows a clearer "reconnecting" message instead of a bare 503

### Migrated to OpenRouter
- Replaced Ollama Cloud (chat) and Google Gemini (embeddings + fallback) with OpenRouter
- Chat model: `deepseek/deepseek-v4-flash` (OpenAI-compatible API via the `openai` SDK)
- Removed Gemini fallback path; rely on OpenRouter's built-in cross-provider failover
- New env vars: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`

### Switched from RAG to full context
- The résumé (~2.4K tokens) is now injected whole into every prompt instead of FAISS
  retrieval — eliminating retrieval misses (e.g. enterprise customers, AI/LLM skills)
- Removed FAISS, embeddings, and the startup index build; `rag_engine` now just loads
  and caches the résumé (R2 in prod, local PDF for dev/evals)
- Fixed a latent bug: `as_retriever(k=3)` was ignored (k belongs in `search_kwargs`)
- Dropped deps: `langchain*`, `faiss-cpu`, `numpy`
- Anchored resume/index paths to the module dir (CWD-independent)

### Added evals
- promptfoo suite (`evals/`) for answer-quality, behavior, and model bake-offs over the
  real pipeline; LLM-as-judge via OpenRouter; 25 résumé-grounded draft cases generator

## v2.0.0 - 2026-03-29

### Analytics Dashboard
- Added a private analytics dashboard at `/admin/dashboard` (token-protected)
- Tracks every chat question, LLM provider used, response latency, and errors
- Visitor tracking: IP geolocation (city/country), browser/device detection, session IDs
- Dashboard shows: total questions, unique visitors, top locations, LLM provider breakdown, most asked questions, recent errors
- Powered by Supabase (Postgres) with async connection pooling via `asyncpg`
- Graceful degradation: app continues running if database is unreachable

### Conversational Responses
- Rewrote system prompt to be conversational instead of resume-dump style
- Bot now matches the energy of the message (greetings get 1-2 sentences, not a wall of text)
- Responses capped at ~60 words unless detail is specifically requested
- Simplified per-request prompt to avoid duplicating tone instructions
- Shorter, friendlier greeting message

### Bug Fixes
- Fixed `get_relevant_documents` deprecation (now uses `invoke()` for langchain 1.2.x)
- Fixed `text-embedding-004` model not found on v1beta API (switched to `gemini-embedding-001`)
- Fixed R2 resume key mismatch (`resume.pdf` -> `embeddings-resume-amit.pdf`)
- Fixed `langchain.text_splitter` import path for langchain 1.2.x

## v1.0.0 - 2026-03-28

### SSE Streaming
- Added `POST /api/chat/stream` endpoint with Server-Sent Events
- Tokens stream progressively instead of waiting for full response
- Gemini 2.0 Flash as primary LLM with Claude Sonnet fallback

### LLM Migration
- Switched from OpenAI to Google Gemini + Anthropic Claude
- Google Generative AI embeddings for RAG vector store
- FAISS vector store with resume context from Cloudflare R2

### Core Features
- FastAPI backend with API key authentication
- Rate limiting via slowapi (5 requests/minute)
- RAG pipeline: PDF resume -> embeddings -> FAISS -> context-aware responses
- Resume storage on Cloudflare R2
- Deployed on Railway with Nixpacks
