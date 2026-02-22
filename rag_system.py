# rag_system_best.py
import os
import warnings
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_cohere import ChatCohere
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

PERSIST_DIRECTORY = "eca_products_vector_db"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-r-plus-08-2024")

# Silence warnings
warnings.filterwarnings(
    "ignore",
    message="The tokenizer you are loading from .* incorrect regex pattern.*",
)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("tokenizers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

def load_embedding() -> HuggingFaceEmbeddings:
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"

    explicit_dir = os.getenv(
        "HF_MODEL_DIR",
        os.path.join("models_cache", "paraphrase-multilingual-MiniLM-L12-v2"),
    )

    if os.path.isdir(explicit_dir):
        return HuggingFaceEmbeddings(
            model_name=explicit_dir,
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )

    # fallback caches
    cache_paths = [
        "./models_cache",
        os.path.expanduser("~/.cache/huggingface/hub"),
        os.path.expanduser("~/.cache/torch/sentence_transformers"),
    ]

    last_error = None
    for cache in cache_paths:
        try:
            return HuggingFaceEmbeddings(
                model_name=MODEL_NAME,
                model_kwargs={"device": "cpu", "local_files_only": True},
                encode_kwargs={"normalize_embeddings": True},
                cache_folder=cache,
            )
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        "Embedding model not found in local cache. "
        "Run ingest once with internet/VPN to cache it. "
        f"Last error: {last_error}"
    )

def load_vectorstore(persist_directory: str) -> Chroma:
    if not Path(persist_directory).exists():
        raise FileNotFoundError(f"Vector DB not found: {persist_directory}")
    embedding = load_embedding()
    return Chroma(persist_directory=persist_directory, embedding_function=embedding)

@lru_cache(maxsize=1)
def list_categories(data_dir: str = "eca_products_merged"):
    path = Path(data_dir)
    if not path.exists():
        return []
    return [p.name for p in path.iterdir() if p.is_dir()]

@lru_cache(maxsize=128)
def list_sources(category: str, data_dir: str = "eca_products_merged"):
    path = Path(data_dir) / category
    if not path.exists():
        return []
    return [p.name for p in path.iterdir() if p.is_file()]

def normalize_name(name: str) -> str:
    name = name.replace("_merged.txt", "").replace(".txt", "")
    for ch in ("_", "-", "(", ")", "[", "]"):
        name = name.replace(ch, " ")
    return " ".join(name.split()).strip().lower()

def detect_source(query: str, category: str, data_dir: str = "eca_products_merged") -> Optional[str]:
    q = normalize_name(query)
    candidates = list_sources(category, data_dir)
    scored = []
    for src in candidates:
        base = normalize_name(src)
        if base and base in q:
            scored.append((len(base), src))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]

def detect_category(query: str, data_dir: str = "eca_products_merged") -> Optional[str]:
    q = query.strip()
    if not q:
        return None
    categories = list_categories(data_dir)
    for cat in sorted(categories, key=len, reverse=True):
        if cat and cat in q:
            return cat
    return None

def build_chain(retriever, llm):
    template = (
        "You are a professional assistant for an electronics components store.\n"
        "Use the context to answer the question.\n"
        "You MAY rephrase, clean, and correct Persian text while keeping facts unchanged.\n"
        "Do NOT invent prices or specifications.\n"
        "If information is missing, clearly say it is not available.\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}\n\n"
        "Answer in fluent, professional Persian."
    )

    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        # dedup automatic
        seen = set()
        results = []
        for doc in docs:
            content = doc.page_content.strip()
            if content not in seen:
                seen.add(content)
                results.append(content)
        return "\n\n".join(results)

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

def run(query: str, show_sources: bool = False, category: Optional[str] = None, source: Optional[str] = None) -> str:
    load_dotenv()
    api_key = os.getenv("COHERE_API_KEY", "")

    vectorstore = load_vectorstore(PERSIST_DIRECTORY)
    detected = category or detect_category(query)
    detected_source = source
    if detected and not detected_source:
        detected_source = detect_source(query, detected)

    search_kwargs = {"k": 3, "fetch_k": 6, "lambda_mult": 0.5}  # MMR retriever
    if detected_source:
        search_kwargs["filter"] = {"source": detected_source}
    elif detected:
        search_kwargs["filter"] = {"category": detected}

    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs=search_kwargs)
    docs = retriever.invoke(query)

    # fallback if nothing found
    if (detected or detected_source) and not docs:
        retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 4, "fetch_k": 8, "lambda_mult": 0.5})
        docs = retriever.invoke(query)

    if show_sources:
        if detected_source:
            print(f"[source filter] {detected_source}")
        elif detected:
            print(f"[category filter] {detected}")
        for i, doc in enumerate(docs, 1):
            print(f"[{i}] {doc.metadata.get('category', 'N/A')} :: {doc.metadata.get('source', 'N/A')}")

    if not api_key:
        return "Cohere API key not set. Showing sources only."

    llm = ChatCohere(model=COHERE_MODEL, cohere_api_key=api_key, temperature=0.3, max_tokens=800)
    chain = build_chain(retriever, llm)
    return chain.invoke(query)

# direct helper for code usage
def ask(query: str, show_sources: bool = False):
    """Simple helper: direct code usage without CLI"""
    return run(query, show_sources=show_sources)

# optional CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="")
    parser.add_argument("--show-sources", action="store_true")
    parser.add_argument("--category", default="")
    parser.add_argument("--source", default="")
    args = parser.parse_args()

    query = args.query.strip() or input("Enter your question: ").strip()
    if not query:
        print("No query provided.")
    else:
        answer = run(query, show_sources=args.show_sources, category=(args.category or None), source=(args.source or None))
        print("\nAnswer:\n" + answer)
