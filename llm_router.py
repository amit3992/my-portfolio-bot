import os
import time
import json
import logging
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT = (
    "You are Veda, a friendly and conversational AI assistant on Amit Kulkarni's portfolio website. "
    "You help visitors learn about Amit's professional background.\n\n"
    "IMPORTANT RULES:\n"
    "- Match the energy of the message. If someone says 'hi' or 'hello', just greet them "
    "back in 1-2 short sentences and ask what they'd like to know. Do NOT dump information.\n"
    "- Keep responses short and natural — like a real conversation, not a resume recitation.\n"
    "- Only share details when specifically asked. Give 2-3 key points, not everything.\n"
    "- Use a warm, casual tone. No corporate speak.\n"
    "- If asked something you don't know from the provided context, say so honestly. "
    "Don't guess or make up details about Amit.\n"
    "- ONLY use facts from the provided context. Never invent roles, titles, preferences, "
    "or details not explicitly stated in the context.\n"
    "- For non-resume questions, gently steer back: 'I'm best at answering questions about Amit!'\n"
    "- Never start responses with 'Great question!' or similar filler.\n"
    "- Keep most responses under 60 words. Only go longer if the question genuinely needs detail.\n"
    "- You have conversation history — use it to understand follow-up questions. "
    "If someone says 'yes', 'tell me more', etc., refer to what was discussed previously.\n"
    "- Your name is Veda. If someone asks why you're called Veda or what your name means, "
    "explain that Veda comes from Sanskrit meaning 'knowledge' — fitting for an assistant "
    "that shares knowledge about Amit. Only mention this when explicitly asked about your name.\n"
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel(
    "gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT,
)


# --- Non-streaming (existing) ---

def get_llm_reply(prompt: str) -> str:
    try:
        return query_ollama(prompt)
    except Exception:
        return query_gemini(prompt)


def query_ollama(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
        json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
        timeout=30,
    )
    resp.raise_for_status()
    return format_chatbot_response(resp.json()["message"]["content"])


def query_gemini(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return format_chatbot_response(response.text)


# --- Streaming ---

def stream_llm_reply(prompt: str, history: list[dict] = None):
    """Yields tokens. Accepts optional conversation history."""
    start = time.time()
    provider = "ollama"
    is_fallback = False
    is_error = False
    error_message = None
    accumulated = ""

    try:
        for chunk in stream_ollama(prompt, history):
            accumulated += chunk
            yield chunk
    except Exception as e:
        logger.warning(f"Ollama failed, falling back to Gemini: {e}")
        is_fallback = True
        provider = "gemini"
        accumulated = ""
        try:
            for chunk in stream_gemini(prompt, history):
                accumulated += chunk
                yield chunk
        except Exception as e2:
            logger.error(f"Gemini fallback also failed: {e2}")
            is_error = True
            error_message = str(e2)

    latency_ms = int((time.time() - start) * 1000)
    stream_llm_reply._last_meta = {
        "provider": provider,
        "is_fallback": is_fallback,
        "is_error": is_error,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "response_preview": accumulated[:200] if accumulated else None,
    }


def stream_ollama(prompt: str, history: list[dict] = None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    with httpx.stream(
        "POST",
        f"{OLLAMA_BASE_URL}/api/chat",
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
        json={"model": OLLAMA_MODEL, "messages": messages, "stream": True},
        timeout=60,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            token = data.get("message", {}).get("content", "")
            if token:
                yield token


def stream_gemini(prompt: str, history: list[dict] = None):
    contents = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    response = gemini_model.generate_content(contents, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text


def format_chatbot_response(content: str) -> str:
    lines = content.split('\n')
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            formatted_lines.append(stripped[2:])
        elif stripped.startswith('* '):
            formatted_lines.append(stripped[2:])
        elif stripped.startswith('• '):
            formatted_lines.append(stripped[2:])
        else:
            formatted_lines.append(line)

    return '\n'.join(formatted_lines)
