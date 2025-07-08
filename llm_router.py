import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
import requests
from dotenv import load_dotenv

load_dotenv()
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def get_llm_reply(prompt: str) -> str:
    return query_openai(prompt)


def query_openai(prompt: str) -> str:
    completion = client.chat.completions.create(model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are Amit's resume assistant, representing Amit Kulkarni, a software engineer with expertise in distributed systems, cloud architecture, and AI/ML. Your purpose is to answer questions about Amit's skills, experience, education, and professional background.\n\n- Respond succinctly in bullet points when possible\n- Keep responses under 150 words unless detailed information is specifically requested\n- Focus on technical skills, work experience, and educational background\n- Maintain a professional yet approachable tone\n- If you don't know an answer, say so directly rather than speculating\n- For technical topics, provide specific examples from Amit's experience\n- For non-resume questions, politely redirect to resume-related information\n"},
        {"role": "user", "content": prompt},
    ])
    
    # Get the raw content from the LLM
    raw_content = completion.choices[0].message.content
    
    # Format the response to be more chatbot-friendly
    formatted_response = format_chatbot_response(raw_content)
    
    return formatted_response


def query_ollama_mistral(prompt: str) -> str:
    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": "You are Amit's resume assistant, representing Amit Kulkarni, a software engineer with expertise in distributed systems, cloud architecture, and AI/ML. Your purpose is to answer questions about Amit's skills, experience, education, and professional background.\n\n- Respond succinctly in bullet points when possible\n- Keep responses under 150 words unless detailed information is specifically requested\n- Focus on technical skills, work experience, and educational background\n- Maintain a professional yet approachable tone\n- If you don't know an answer, say so directly rather than speculating\n- For technical topics, provide specific examples from Amit's experience\n- For non-resume questions, politely redirect to resume-related information\n"},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload)
    
    # Get the raw content from the LLM
    raw_content = response.json()["message"]["content"]
    
    # Format the response to be more chatbot-friendly
    formatted_response = format_chatbot_response(raw_content)
    
    return formatted_response


def format_chatbot_response(content: str) -> str:
    """
    Format the raw LLM response to be more chatbot-friendly by converting bullet points
    to conversational text without adding automatic greetings or closing messages.
    
    Args:
        content: The raw content from the LLM response
        
    Returns:
        A formatted, chatbot-friendly response without added greetings or closings
    """
    # Convert bullet points to a more conversational format
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Remove bullet points and convert to conversational text
        if line.strip().startswith('- '):
            formatted_lines.append(line.strip()[2:])
        elif line.strip().startswith('* '):
            formatted_lines.append(line.strip()[2:])
        elif line.strip().startswith('• '):
            formatted_lines.append(line.strip()[2:])
        else:
            formatted_lines.append(line)
    
    # Join the lines with proper spacing
    formatted_content = '\n'.join(formatted_lines)
    
    return formatted_content
