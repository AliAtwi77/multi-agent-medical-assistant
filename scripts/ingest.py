from backend.rag.retrievers import get_ensemble_retriever, PUBMED_INGEST_LIMIT, stores_exist
from backend.utils.logger import logger
import sys
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-warm the PubMed retriever stores (Chroma + BM25).")
    parser.add_argument("--limit", type=int, default=PUBMED_INGEST_LIMIT, help="Number of PubMed rows to load.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if persisted stores already exist.")
    args = parser.parse_args()

    if not args.force and stores_exist():
        logger.info("Persisted retriever stores already exist on disk — nothing to do. "
                     "Pass --force to rebuild anyway.")
        sys.exit(0)

    try:
        get_ensemble_retriever(limit=args.limit, force_rebuild=args.force)
        logger.info("Retriever stores are ready. Future startups will load them instantly from disk.")
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user.")
        sys.exit(1)