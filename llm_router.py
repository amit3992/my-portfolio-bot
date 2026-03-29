import os
import google.generativeai as genai
import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are Amit's resume assistant, representing Amit Kulkarni, a software engineer "
    "with expertise in distributed systems, cloud architecture, and AI/ML. Your purpose "
    "is to answer questions about Amit's skills, experience, education, and professional "
    "background.\n\n"
    "- Respond succinctly in bullet points when possible\n"
    "- Keep responses under 150 words unless detailed information is specifically requested\n"
    "- Focus on technical skills, work experience, and educational background\n"
    "- Maintain a professional yet approachable tone\n"
    "- If you don't know an answer, say so directly rather than speculating\n"
    "- For technical topics, provide specific examples from Amit's experience\n"
    "- For non-resume questions, politely redirect to resume-related information\n"
)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel(
    "gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT,
)

claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_llm_reply(prompt: str) -> str:
    try:
        return query_gemini(prompt)
    except Exception:
        return query_claude(prompt)


def query_gemini(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    raw_content = response.text
    return format_chatbot_response(raw_content)


def query_claude(prompt: str) -> str:
    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_content = message.content[0].text
    return format_chatbot_response(raw_content)


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
