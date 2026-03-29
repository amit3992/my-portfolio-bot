from fastapi import FastAPI, Request, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from rag_engine import get_retriever
from llm_router import get_llm_reply, stream_llm_reply
from database import init_db, close_db, log_chat_event, get_knowledge_snippets
from dashboard import router as dashboard_router
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
import json
import os

load_dotenv()


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield
    await close_db()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key_header

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(dashboard_router)


@app.get("/api/greeting")
async def get_greeting():
    return {
        "greeting": "Hey! I'm Amit's AI assistant. Ask me anything about his work, skills, or experience."
    }

async def build_prompt(user_input: str) -> str:
    context_chunks = get_retriever().invoke(user_input)
    context = " ".join([doc.page_content for doc in context_chunks])

    snippets = await get_knowledge_snippets()
    snippet_text = ""
    if snippets:
        snippet_text = "\n\nAdditional context:\n" + "\n".join(
            f"- {s['content']}" for s in snippets
        )

    return f"Context from Amit's resume: {context}{snippet_text}\n\nVisitor's message: {user_input}"


@app.post("/api/chat")
@limiter.limit("5/minute")
async def chat(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    user_input = data["message"]
    prompt = await build_prompt(user_input)

    reply = get_llm_reply(prompt)
    return {"reply": reply}


@app.post("/api/chat/stream")
@limiter.limit("5/minute")
async def chat_stream(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    user_input = data["message"]
    ip_address = get_remote_address(request)
    session_id = request.headers.get("X-Session-ID")
    user_agent = request.headers.get("User-Agent")
    prompt = await build_prompt(user_input)

    async def event_generator():
        for chunk in stream_llm_reply(prompt):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
        yield "data: [DONE]\n\n"

        # Log after streaming completes
        meta = getattr(stream_llm_reply, "_last_meta", {})
        await log_chat_event(
            user_question=user_input,
            llm_provider=meta.get("provider"),
            response_preview=meta.get("response_preview"),
            latency_ms=meta.get("latency_ms"),
            is_error=meta.get("is_error", False),
            error_message=meta.get("error_message"),
            is_fallback=meta.get("is_fallback", False),
            ip_address=ip_address,
            endpoint="/api/chat/stream",
            session_id=session_id,
            user_agent=user_agent,
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
