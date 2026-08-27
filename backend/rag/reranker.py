#reranker.py
from functools import lru_cache
from sentence_transformers import CrossEncoder
from backend.utils.logger import logger
from backend.config.settings import RERANKER_MODEL, RERANKER_TOP_K


@lru_cache
def _get_reranker()-> CrossEncoder:
    logger.info(f"Loading reranker model: {RERANKER_MODEL}")
    return CrossEncoder(RERANKER_MODEL)

def rerank(query: str, candidates: list[dict], top_k: int | None = None) -> list[dict]:
    top_k = top_k if top_k is not None else RERANKER_TOP_K
    if not candidates:
        return []
    model = _get_reranker()
    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return ranked[:top_k]


