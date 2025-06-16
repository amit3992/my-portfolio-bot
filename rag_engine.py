from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from load_resume import extract_text_from_pdf
from load_resume import get_resume_from_r2
import os

load_dotenv()

def load_resume_embeddings():
    text = get_resume_from_r2()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_text(text)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_texts(chunks, embedding=embeddings)
    vectorstore.save_local("embeddings")
    print(" Vector DB created locally.")

def load_retriever():
    if not os.path.exists("embeddings"):
        load_resume_embeddings()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local("embeddings", embeddings, allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_type="similarity", k=3)

# Initialize retriever only when imported and used, not at module level
retriever = None

def get_retriever():
    global retriever
    if retriever is None:
        retriever = load_retriever()
    return retriever
