import os
import requests
import json
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from pypdf import PdfReader

# Custom LangChain Embeddings class that leverages the local Ollama API
class OllamaLocalEmbeddings(Embeddings):
    def __init__(self, model="nomic-embed-text:latest"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/embeddings"
        
    def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            try:
                r = requests.post(self.url, json={"model": self.model, "prompt": text}, timeout=10)
                if r.status_code == 200:
                    embeddings.append(r.json()["embedding"])
                else:
                    embeddings.append([0.0] * 768) # Fallback vector
            except Exception as e:
                # print(f"Embed error: {e}")
                embeddings.append([0.0] * 768)
        return embeddings
        
    def embed_query(self, text):
        try:
            r = requests.post(self.url, json={"model": self.model, "prompt": text}, timeout=10)
            if r.status_code == 200:
                return r.json()["embedding"]
        except Exception as e:
            # print(f"Embed query error: {e}")
            pass
        return [0.0] * 768

# Helper to get local path for vector store
def get_chroma_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'chroma_db')

def initialize_vector_store():
    embeddings = OllamaLocalEmbeddings()
    db_path = get_chroma_path()
    return Chroma(persist_directory=db_path, embedding_function=embeddings)

def ingest_medical_documents():
    """
    Parses all PDFs in medical_docs/ and indexes them in ChromaDB.
    Also extracts all Medicine entries from SQLite and indexes them for semantic search.
    """
    print("[RAG Ingestion] Starting clinical document and inventory ingestion...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.abspath(os.path.join(base_dir, '..', 'medical_docs'))
    
    chunks = []
    
    # 1. Process PDFs
    if os.path.exists(docs_dir):
        for file in os.listdir(docs_dir):
            if file.endswith('.pdf'):
                pdf_path = os.path.join(docs_dir, file)
                try:
                    reader = PdfReader(pdf_path)
                    text = ""
                    for idx, page in enumerate(reader.pages):
                        text += page.extract_text() + "\n"
                    
                    # Split PDF text
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
                    file_chunks = text_splitter.split_text(text)
                    for chunk in file_chunks:
                        chunks.append({
                            "text": f"[Source: {file}]\n{chunk}",
                            "metadata": {"source": file, "type": "clinical_guide"}
                        })
                    print(f"[RAG Ingestion] Split {file} into {len(file_chunks)} chunks.")
                except Exception as e:
                    print(f"[RAG Ingestion] Error reading PDF {pdf_path}: {e}")
    else:
        print(f"[RAG Ingestion] Docs directory not found at {docs_dir}")
        
    # 2. Process Medicine Inventory from SQLite
    try:
        from store.models import Medicine
        all_medicines = Medicine.objects.all()
        med_count = 0
        for med in all_medicines:
            rx_text = "Prescription REQUIRED (Rx)" if med.is_prescription_required else "Over-the-Counter (OTC)"
            med_info = (
                f"Medicine Name: {med.name}\n"
                f"Category: {med.category.name} | Brand: {med.brand_name}\n"
                f"Generic Name: {med.generic_name} | Active Ingredient: {med.active_ingredient}\n"
                f"Price: INR {med.price} | Stock: {med.stock} units | Expiry: {med.expiry_date}\n"
                f"Class: {rx_text} | Warehouse Location: {med.warehouse_location}\n"
                f"Description: {med.description}"
            )
            chunks.append({
                "text": f"[Source: Shop Inventory]\n{med_info}",
                "metadata": {"source": "shop_db", "type": "medicine_product", "med_id": med.id}
            })
            med_count += 1
        print(f"[RAG Ingestion] Indexed {med_count} medicines from SQLite database.")
    except Exception as e:
        print(f"[RAG Ingestion] Error importing or parsing medicines: {e}")

    if not chunks:
        print("[RAG Ingestion] No content found to ingest.")
        return False
        
    # Load into Chroma DB
    try:
        db_path = get_chroma_path()
        # Clean existing store directory
        if os.path.exists(db_path):
            import shutil
            shutil.rmtree(db_path)
            
        embeddings = OllamaLocalEmbeddings()
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        db = Chroma.from_texts(texts, embeddings, metadatas=metadatas, persist_directory=db_path)
        print(f"[RAG Ingestion] Successfully loaded {len(chunks)} chunks into ChromaDB at {db_path}.")
        return True
    except Exception as e:
        print(f"[RAG Ingestion] ChromaDB loading failed: {e}")
        return False

def query_local_ollama(prompt, system_prompt=None, model="llama3:latest"):
    """
    Sends request directly to the local Ollama service REST endpoint.
    """
    url = "http://127.0.0.1:11434/api/chat"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=40)
        if r.status_code == 200:
            return r.json()["message"]["content"]
        else:
            return f"Error: Local model service returned status code {r.status_code}"
    except Exception as e:
        return f"Error connecting to local Ollama server: {e}"

def search_similar_documents(query, limit=5, type_filter=None):
    """
    Performs semantic vector search against local ChromaDB.
    """
    try:
        db = initialize_vector_store()
        filter_dict = {}
        if type_filter:
            filter_dict = {"type": type_filter}
            
        if filter_dict:
            results = db.similarity_search(query, k=limit, filter=filter_dict)
        else:
            results = db.similarity_search(query, k=limit)
        return results
    except Exception as e:
        print(f"[RAG Search] Search failed: {e}")
        return []
