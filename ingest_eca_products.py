# -*- coding: utf-8 -*-

import os
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

BASE_DIR = "eca_products_merged"  # مسیر رو اصلاح کردم

# -----------------------------
# Load TXT documents
# -----------------------------
documents: list[Document] = []

print(f"Checking directory: {BASE_DIR}")
if not os.path.exists(BASE_DIR):
    print(f"❌ Directory {BASE_DIR} does not exist!")
    exit(1)

for category in os.listdir(BASE_DIR):
    category_path = os.path.join(BASE_DIR, category)

    if not os.path.isdir(category_path):
        continue

    print(f"Processing category: {category}")
    
    for filename in os.listdir(category_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(category_path, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "category": category,
                            "source": filename,
                        }
                    )
                )
                print(f"  Loaded: {filename}")
            except Exception as e:
                print(f"  Error loading {filename}: {e}")

print(f"\n✅ Loaded documents: {len(documents)}")

if len(documents) == 0:
    print("❌ No documents loaded! Exiting.")
    exit(1)

# -----------------------------
# Split documents
# -----------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

chunks = text_splitter.split_documents(documents)

print(f"📄 Total chunks: {len(chunks)}")

# -----------------------------
# Embedding model (HuggingFace - local)
# -----------------------------
print("🔄 Loading embedding model...")
embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},  # اگر GPU دارید، می‌تونید 'cuda' بذارید
    encode_kwargs={'normalize_embeddings': True}
)

# تست embedding
vec = embedding.embed_query("دیود پل 10 آمپر 1000 ولت")
print(f"✅ Embedding vector size: {len(vec)}")

# -----------------------------
# Create Final Vector DB
# -----------------------------
print("🔄 Creating vector database...")
persist_directory = "eca_products_vector_db"

# اگه دایرکتوری قبلی وجود داره، پاکش می‌کنیم
if os.path.exists(persist_directory):
    import shutil
    print(f"Removing existing {persist_directory}")
    shutil.rmtree(persist_directory)

# ایجاد vector store با تمام chunks
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding,
    persist_directory=persist_directory
)

print(f"✅ Final Vector DB created and persisted to {persist_directory}")

# -----------------------------
# Test the vector store
# -----------------------------
print("\n🔄 Testing similarity search...")
test_queries = [
    "دیود پل 10 آمپر 1000 ولت",
    "مقاومت SMD 10 کیلواهم",
    "آی سی رگولاتور 7805"
]

for query in test_queries:
    print(f"\n📝 Query: {query}")
    results = vectorstore.similarity_search(query, k=2)
    
    for i, doc in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"  Category: {doc.metadata.get('category', 'N/A')}")
        print(f"  Source: {doc.metadata.get('source', 'N/A')}")
        print(f"  Preview: {doc.page_content[:150]}...")
        print("-" * 50)

print("\n✅ All done!")