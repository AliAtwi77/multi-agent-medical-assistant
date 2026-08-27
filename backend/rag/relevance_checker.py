#relevance_checker.py
from pydantic import BaseModel, Field
from backend.utils.logger import logger
from backend.config.llm_clients import get_small_llm
from backend.config.settings import RELEVANCE_CHECK_CHUCK_CHARS
from langchain.messages import SystemMessage, HumanMessage
from backend.config.prompts import RELEVANCE_CHECK_SYSTEM_PROMPT



class ChunkVerdict(BaseModel):
    chunk_id: str = Field(description="The chunk_id exactly as given in the input.")
    is_relevant: bool = Field(description="True if this chunk contains information that helps answer the query.")
    reason: str = Field(description="One short sentence explaining the verdict.")

class RelevanceCheckResult(BaseModel):
    verdicts: list[ChunkVerdict]


def check_relevance(query: str, chunks: list[dict]) -> tuple[list[dict], list[dict]]:
    
    if not chunks:
        return [], []

    try:
        llm = get_small_llm().with_structured_output(RelevanceCheckResult)
        chunk_block = "\n\n".join(
            f"chunk_id: {c['chunk_id']}\ntext: {c['text']}" for c in chunks
        )
        result: RelevanceCheckResult = llm.invoke([
            SystemMessage(content=RELEVANCE_CHECK_SYSTEM_PROMPT),
            HumanMessage(content=f"Query: {query}\n\nChunks:\n{chunk_block}"),
        ])

        verdict_by_id = {v.chunk_id: v.is_relevant for v in result.verdicts}
        relevant = [c for c in chunks if verdict_by_id.get(c["chunk_id"], True)]
        irrelevant = [c for c in chunks if not verdict_by_id.get(c["chunk_id"], True)]

        logger.info(f"Relevance check: {len(relevant)} relevant / {len(irrelevant)} irrelevant of {len(chunks)}")
        return relevant, irrelevant
    except Exception as e:
        logger.error(f"Relevance checker failed, treating all chunks as relevant (fail-open): {e}")
        return chunks, []



