from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from rag_engine import get_retriever
from llm_router import get_llm_reply
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/api/greeting")
async def get_greeting():
    return {
        "greeting": """Hi there! 👋 I'm Amit's AI assistant, and I'm here to help you learn more about him. 
        I can tell you about his work experience, skills, projects, and achievements. Feel free to ask me anything!"""
    }

@app.post("/api/chat")
@limiter.limit("5/minute")  # Allow 5 requests per minute per IP
async def chat(request: Request):
    data = await request.json()
    user_input = data["message"]
    context_chunks = get_retriever().get_relevant_documents(user_input)
    context = " ".join([doc.page_content for doc in context_chunks])

    prompt = f"""
    You are a friendly and helpful AI assistant for Amit Kulkarni. Your role is to provide informative 
    and engaging responses about Amit's professional background, skills, and experiences. Maintain a 
    conversational and warm tone while being precise and factual.

    Use this context to inform your response: {context}
    
    User's question: {user_input}
    """

    reply = get_llm_reply(prompt)
    return {"reply": reply}
