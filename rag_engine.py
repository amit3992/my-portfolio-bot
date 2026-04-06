from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from dotenv import load_dotenv
from load_resume import get_resume_from_r2
import httpx
import os

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


class OllamaCloudEmbeddings(Embeddings):
    """LangChain-compatible embeddings using Ollama Cloud API."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embed",
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
            json={"model": OLLAMA_EMBED_MODEL, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def get_embeddings():
    return OllamaCloudEmbeddings()


def load_resume_embeddings():
    text = get_resume_from_r2()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_text(text)
    vectorstore = FAISS.from_texts(chunks, embedding=get_embeddings())
    vectorstore.save_local("embeddings")
    print(" Vector DB created locally.")

def load_retriever():
    if not os.path.exists("embeddings"):
        load_resume_embeddings()
    vectorstore = FAISS.load_local("embeddings", get_embeddings(), allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_type="similarity", k=3)

retriever = None

def get_retriever():
    global retriever
    if retriever is None:
        retriever = load_retriever()
    return retriever
