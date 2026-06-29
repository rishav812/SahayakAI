import os
import chromadb
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from app.config import embeddings, CHROMA_DIR, COLLECTION


def load_chunks():
    os.makedirs("data", exist_ok=True)
    txt_docs = DirectoryLoader("data/", glob="**/*.txt", loader_cls=TextLoader).load()
    pdf_docs = DirectoryLoader("data/", glob="**/*.pdf", loader_cls=PyPDFLoader).load()
    docs = txt_docs + pdf_docs
    if not docs:
        print("No documents found in 'data/' directory.")
        return []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    print(f"Loaded {len(docs)} pages -> {len(chunks)} chunks")
    return chunks


def ingest():
    chunks = load_chunks()
    if not chunks:
        raise ValueError("No files found in data/")

    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        client.delete_collection(COLLECTION)
        print(f"Deleted existing collection '{COLLECTION}'.")
    except Exception:
        pass

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
    )
    print(f"Ingested {len(chunks)} chunks into '{COLLECTION}'.")
    return chunks


if __name__ == "__main__":
    ingest()
