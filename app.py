from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from rag_engine import get_retriever
from llm_router import get_llm_reply

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data["message"]
    context_chunks = get_retriever().get_relevant_documents(user_input)
    context = " ".join([doc.page_content for doc in context_chunks])

    prompt = f"""
    You are a chatbot that answers questions about Amit Kulkarni's resume and work.
    Use this context: {context}
    Question: {user_input}
    """

    reply = get_llm_reply(prompt)
    return {"reply": reply}
