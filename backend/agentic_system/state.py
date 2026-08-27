from typing import TypedDict, Optional, Literal


class SourceDict(TypedDict, total=False):
    document: str
    chunk_id: str
    page: Optional[int]
    snippet: str


class AgentState(TypedDict, total=False):
    # input
    conversation_id: str
    user_query: str
    image_id: Optional[str]
    chat_history: list[dict]  # [{"role": ..., "content": ...}]

    # routing
    route: Literal["rag", "web_search", "image_analysis", "general", "blocked"]
    guardrail_passed: bool
    guardrail_reason: str

    # RAG
    expanded_queries: list[str]
    reranked_chunks: list[dict]
    relevant_chunks: list[dict]          # subset of reranked_chunks that passed the relevance check
    irrelevant_chunks: list[dict]        # subset that failed — dropped and backfilled with web results
    web_supplement_results: list[dict]   # web search results backfilled in place of irrelevant_chunks
    rag_answer: str
    rag_confidence: float

    # Web search
    web_results: list[dict]
    web_answer: str
    web_confidence: float

    # Image
    image_findings: str
    image_confidence: float

    # final
    final_answer: str
    agent_used: str
    confidence: float
    needs_human_review: bool
    sources: list[SourceDict]
