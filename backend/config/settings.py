from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv()
medgemma_base_url = os.getenv("MEDGEMMA_BASE_URL")
BASE_DIR = Path(__file__).resolve().parents[2]
# LLM
CHAT_MODEL = "claude-sonnet-4-6"
SMALL_MODEL = "claude-haiku-4-5-20251001"

# Web Search
EXA_MAX_SEARCH_RESULTS= 5

# Voice
ELEVENSLABS_STT_MODEL = "scribe_v2"
ELEVENSLABS_TTS_MODEL = "eleven_flash_v2_5"
ELEVENSLABS_VOICE_ID = "DXFkLCBUTmvXpp2QwZjA"

# Imaging - MEDGEMMA
MEDGEMMA_BASE_URL = medgemma_base_url
MEDGEMMA_MODEL_NAME = "google/medgemma-1.5-4b-it"
MEDGEMMA_MAX_TOKEN= 512
MEDGEMMA_TEMPERATURE= 0.2
MEDGEMMA_TOP_P= 0.8

# RAG
DATASET_NAME= "MedRAG/pubmed"
    #Embedding /Reranker
EMBEDDING_MODEL = "NeuML/pubmedbert-base-embeddings"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L12-v2"
    #Vector_DB
CHROMA_PERSIST_DIR= BASE_DIR / "data" / "vector_store"
CHROMA_COLLECTION= "medical_pubmed"
BM25_INDEX_PATH:str = BASE_DIR / "data" / "vector_store"/ "bm25_retriever.pkl"
PUBMED_INGEST_LIMIT= 10000
BATCH_SIZE= 500
RETRIEVAL_TOP_K= 10
RERANKER_TOP_K=4
RELEVANCE_CHECK_CHUCK_CHARS= 750
ENSEMBLE_WEIGHTS= [0.6, 0.4]
QUERY_EXPANSION_MAX_VARIANTS= 3

# App
APP_ENV = "development"
SQLITE_DB_PATH = BASE_DIR / "data" / "app.db"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
CORS_ORIGINS = "http://localhost:5500"
CONFIDENCE_THRESHOLD = 0.5
LOG_LEVEL = "INFO"