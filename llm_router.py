import os
import time
import json
import logging
import google.generativeai as genai
import anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT = (
    "You are a friendly, conversational assistant on Amit Kulkarni's portfolio website. "
    "You help visitors learn about Amit's professional background.\n\n"
    "IMPORTANT RULES:\n"
    "- Match the energy of the message. If someone says 'hi' or 'hello', just greet them "
    "back in 1-2 short sentences and ask what they'd like to know. Do NOT dump information.\n"
    "- Keep responses short and natural — like a real conversation, not a resume recitation.\n"
    "- Only share details when specifically asked. Give 2-3 key points, not everything.\n"
    "- Use a warm, casual tone. No corporate speak.\n"
    "- If asked something you don't know, say so briefly.\n"
    "- For non-resume questions, gently steer back: 'I'm best at answering questions about Amit!'\n"
    "- Never start responses with 'Great question!' or similar filler.\n"
    "- Keep most responses under 60 words. Only go longer if the question genuinely needs detail.\n"
)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel(
    "gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT,
)

claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# --- Non-streaming (existing) ---

def get_llm_reply(prompt: str) -> str:
    try:
        return query_gemini(prompt)
    except Exception:
        return query_claude(prompt)


def query_gemini(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return format_chatbot_response(response.text)


def query_claude(prompt: str) -> str:
    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return format_chatbot_response(message.content[0].text)


# --- Streaming ---

def stream_llm_reply(prompt: str):
    """Yields (token, metadata_dict) — metadata only on the final yield."""
    start = time.time()
    provider = "gemini"
    is_fallback = False
    is_error = False
    error_message = None
    accumulated = ""

    try:
        first = True
        for chunk in stream_gemini(prompt):
            if first:
                first = False
            accumulated += chunk
            yield chunk
    except Exception as e:
        logger.warning(f"Gemini failed, falling back to Claude: {e}")
        is_fallback = True
        provider = "claude"
        accumulated = ""
        try:
            for chunk in stream_claude(prompt):
                accumulated += chunk
                yield chunk
        except Exception as e2:
            logger.error(f"Claude fallback also failed: {e2}")
            is_error = True
            error_message = str(e2)

    latency_ms = int((time.time() - start) * 1000)
    # Attach metadata to the generator for the caller to read
    stream_llm_reply._last_meta = {
        "provider": provider,
        "is_fallback": is_fallback,
        "is_error": is_error,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "response_preview": accumulated[:200] if accumulated else None,
    }


def stream_gemini(prompt: str):
    response = gemini_model.generate_content(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text


def stream_claude(prompt: str):
    with claude_client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


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
