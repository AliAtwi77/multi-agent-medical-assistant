import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers import EnsembleRetriever
from huggingface_hub import list_repo_files, hf_hub_download
from backend.utils.logger import logger
import json
from backend.config.settings import EMBEDDING_MODEL, CHROMA_PERSIST_DIR, BM25_INDEX_PATH, DATASET_NAME, CHROMA_COLLECTION, RETRIEVAL_TOP_K, PUBMED_INGEST_LIMIT, ENSEMBLE_WEIGHTS, BATCH_SIZE
import os
from langchain_core.documents import Document
import time
from datasets import load_dataset
import uuid
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
import pickle
from backend.utils.exceptions import RetrievalError


CHUNK_FILENAME_PATTERN= re.compile(r"^chunk/pubmed23n(\d+)\.jsonl$")

_embeddings: HuggingFaceEmbeddings | None= None
_ensemble_retriever: EnsembleRetriever | None= None


def _get_embeddings()->HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embeddings= HuggingFaceEmbeddings(model_name= EMBEDDING_MODEL)
    return _embeddings


def stores_exist() -> bool:
    """True only if BOTH persisted Chroma store and the pickled BM25 index are present on disk. If either is missing we rebuild both."""
    chroma_dir = CHROMA_PERSIST_DIR
    chroma_has_data= os.path.isdir(chroma_dir) and any(os.scandir(chroma_dir))
    bm25_has_data= os.path.isfile(BM25_INDEX_PATH)
    return chroma_has_data and bm25_has_data


def list_sorted_chunk_files() -> list[str]:
    all_files= list_repo_files(repo_id=DATASET_NAME, repo_type="dataset")
    chunk_files= [f for f in all_files if CHUNK_FILENAME_PATTERN.match(f)]
    if not chunk_files:
        raise RetrievalError(f"No chunk/pubmed23n*.jsonl files found in {DATASET_NAME}")
    chunk_files.sort(key=lambda f: int(CHUNK_FILENAME_PATTERN.match(f).group(1)))
    return chunk_files


def row_to_document(row:dict) -> Document |None:
    content= row.get("contents").strip()
    if not content:
        return None
    pmid= row.get("PMID") or row.get("id") or "unkown"
    return Document(
        page_content=content,
        metadata = {
            "chunk_id": str(uuid.uuid4()),
            "source": f"Pubmed: {pmid}",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if str (pmid).isdigit() else "",
            "page": -1,
        }
    )


def load_pubmed_documents(limit:int) ->list[Document]:
    """Load MedRAG/pubmed dataset and convert each row into a Document with no chunking."""
    chunk_files= list_sorted_chunk_files()
    logger.info(f"Repo has {len(chunk_files)} chunk files available")

    documents: list[Document]= []
    skipped=0
    files_used= 0

    for filename in chunk_files:
        if len(documents) >= limit:
            break

        files_used +=1
        logger.info(f"Downloading {filename} ({files_used} file(s) so far)")
        local_path= hf_hub_download( repo_id= DATASET_NAME, repo_type="dataset", filename=filename)

        with open(local_path, "r", encoding="utf-8") as f:
            for line in f:
                if len(documents) >= limit:
                    break
                line= line.strip()
                if not line:
                    continue
                row= json.loads(line)
                doc= row_to_document(row)
                if doc is None:
                    skipped +=1
                    continue
                documents.append(doc)

    logger.info(f"Built {len(documents)} Documents from {files_used} file(s)")

    return documents


def build_and_persist_documents(limit:int) -> tuple[Chroma,BM25Retriever]:
    """Build and persists Chroma vector store and BM25 sparse index from pubmed documents"""
    documents= load_pubmed_documents(limit=limit)
    embeddings=_get_embeddings()

    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    logger.info("Embedding documents into Chroma")

    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    batch_size = BATCH_SIZE
    total = len(documents)
    logger.info(f"Embedding {total} documents into Chroma in batches of {batch_size} "
                "— this is the slow, one-time step (subsequent startups load this from disk instantly)...")

    started = time.time()
    for start in range(0, total, batch_size):
        batch = documents[start:start + batch_size]
        vectorstore.add_documents(batch)

        done = start + len(batch)
        elapsed = time.time() - started
        rate = done / elapsed if elapsed > 0 else 0
        eta_min = ((total - done) / rate / 60) if rate > 0 else float("nan")
        logger.info(f"Embedded {done}/{total} documents ({rate:.1f} docs/sec, ETA ~{eta_min:.1f} min)")

    logger.info("Chroma store built and persisted to disk.")

    logger.info("Building BM25 sparse index...")
    bm25 = BM25Retriever.from_documents(documents)
    os.makedirs(os.path.dirname(BM25_INDEX_PATH), exist_ok=True)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25, f)
    logger.info(f"BM25 index built and pickled to {BM25_INDEX_PATH}.")

    return vectorstore, bm25


def load_persisted_stores() -> tuple[Chroma,BM25Retriever]:
    """Loads and return persisted stores from disk."""
    logger.info("Persisted retriever stores found on disk, Loading Directly...")
    embeddings= _get_embeddings()
    vectorstore= Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory= CHROMA_PERSIST_DIR,
    )
    with open(BM25_INDEX_PATH, "rb") as f:
        bm25= pickle.load(f)
    return vectorstore, bm25


def get_ensemble_retriever(
        top_k:int= RETRIEVAL_TOP_K,
        limit:int = PUBMED_INGEST_LIMIT,
        force_rebuild:bool= False,
):
    """Initialize or reuses a hybrid Ensemble Retriever combing both Chroma and BM25"""
    global _ensemble_retriever
    if _ensemble_retriever is not None and not force_rebuild:
        return _ensemble_retriever

    try:
        if not force_rebuild and stores_exist():
            vectorstore, bm25= load_persisted_stores()
        else:
            vectorstore, bm25= build_and_persist_documents(limit=limit)

        dense_retriever=vectorstore.as_retriever(search_kwargs={"k": top_k})
        bm25.k = top_k

        _ensemble_retriever= EnsembleRetriever(
            retrievers=[dense_retriever, bm25],
            weights= ENSEMBLE_WEIGHTS,
        )

        return _ensemble_retriever

    except Exception as e:
        raise RetrievalError(f"Failed to initialize retriver stores: {e}") from e


def retrieve(query:str, top_k:int= RETRIEVAL_TOP_K) -> list[dict]:
    """Retrieves relevant document chunks for a given query using hybrid ensemble retriever"""
    try:
        retriever= get_ensemble_retriever(top_k=top_k)
        docs= retriever.invoke(query)
    except RetrievalError:
        raise
    except Exception as e:
        raise RetrievalError(f"Retrieval failed for query: {e}") from e

    results=[]
    for doc in docs:
        meta= doc.metadata or {}
        page= meta.get("page")
        results.append(
            {
                "chunk_id": meta.get("chunk_id", str(uuid.uuid4())),
                "text": doc.page_content,
                "source": meta.get("source", ""),
                "page": page if page not in (None, -1) else None,
                "url": meta.get("url") or None,
            }
        )
    return results
