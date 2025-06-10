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
        {"role": "system", "content": "You are Amit's resume assistant."},
        {"role": "user", "content": prompt},
    ])
    return completion.choices[0].message.content


def query_ollama_mistral(prompt: str) -> str:
    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": "You are Amit's resume assistant."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload)
    return response.json()["message"]["content"]
