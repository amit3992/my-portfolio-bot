import os
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT = (
    "You are Veda, a friendly and conversational AI assistant on Amit Kulkarni's portfolio website. "
    "You help visitors learn about Amit's professional background.\n\n"
    "IMPORTANT RULES:\n"
    "- Match the energy of the message. If someone says 'hi' or 'hello', greet them back in "
    "1-2 short sentences and ask what they'd like to know. In a greeting, do NOT mention "
    "his roles, employers, skills, projects, or any background details — just greet and invite "
    "a question.\n"
    "- Keep responses short and natural — like a real conversation, not a resume recitation.\n"
    "- Only share details when specifically asked. Give 2-3 key points, not everything.\n"
    "- Use a warm, casual tone. No corporate speak.\n"
    "- ONLY use facts from the provided context. Never invent roles, titles, preferences, "
    "or details not explicitly stated in the context.\n"
    "- If the context doesn't mention something (a certification, license, hobby, etc.), do "
    "NOT state that Amit does OR does not have it — you only know what's in the context. Say "
    "you don't have that information, e.g. 'I don't have anything on that — but I can tell you "
    "about his work or projects!' Never assert the absence of a fact as if it were confirmed.\n"
    "- For non-resume questions, gently steer back: 'I'm best at answering questions about Amit!'\n"
    "- Start directly with the answer. Never open with filler such as 'Great question', "
    "'That's a great question', 'Good question', 'Sure!', or any phrase that praises or "
    "restates the question.\n"
    "- Keep most responses under 60 words. Only go longer if the question genuinely needs detail.\n"
    "- You have conversation history — use it to understand follow-up questions. "
    "If someone says 'yes', 'tell me more', etc., refer to what was discussed previously.\n"
    "- Your name is Veda. If someone asks why you're called Veda or what your name means, "
    "explain that Veda comes from Sanskrit meaning 'knowledge' — fitting for an assistant "
    "that shares knowledge about Amit. Only mention this when explicitly asked about your name.\n"
)

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

# Optional attribution headers used for OpenRouter rankings.
_EXTRA_HEADERS = {
    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
    "X-Title": os.getenv("OPENROUTER_SITE_NAME", "Veda Portfolio Bot"),
}

_client = None


def _get_client() -> OpenAI:
    """Lazily build the OpenRouter client so import/startup doesn't require the key."""
    global _client
    if _client is None:
        _client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
    return _client


def _build_messages(prompt: str, history: list[dict] = None) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})
    return messages


# --- Non-streaming ---

def get_llm_reply(prompt: str) -> str:
    return query_openrouter(prompt)


def query_openrouter(prompt: str) -> str:
    completion = _get_client().chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=_build_messages(prompt),
        extra_headers=_EXTRA_HEADERS,
        timeout=30,
    )
    return format_chatbot_response(completion.choices[0].message.content)


# --- Streaming ---

def stream_llm_reply(prompt: str, history: list[dict] = None):
    """Yields tokens. Accepts optional conversation history."""
    start = time.time()
    is_error = False
    error_message = None
    accumulated = ""

    try:
        for chunk in stream_openrouter(prompt, history):
            accumulated += chunk
            yield chunk
    except Exception as e:
        logger.error(f"OpenRouter streaming failed: {e}")
        is_error = True
        error_message = str(e)

    latency_ms = int((time.time() - start) * 1000)
    stream_llm_reply._last_meta = {
        "provider": "openrouter",
        "is_fallback": False,
        "is_error": is_error,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "response_preview": accumulated[:200] if accumulated else None,
    }


def stream_openrouter(prompt: str, history: list[dict] = None):
    stream = _get_client().chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=_build_messages(prompt, history),
        stream=True,
        extra_headers=_EXTRA_HEADERS,
        timeout=60,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        token = chunk.choices[0].delta.content
        if token:
            yield token


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
