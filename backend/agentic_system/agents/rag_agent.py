#rag_agent.py
from backend.agentic_system.state import AgentState
# from backend.rag.query_expantion import expand_query
from backend.rag.retrievers import retrieve
from backend.config.settings import RETRIEVAL_TOP_K, RERANKER_TOP_K
from backend.rag.reranker import rerank
from backend.utils.logger import logger
from backend.rag.relevance_checker import check_relevance
from backend.web_search.exa_client import search_medical_web
from backend.config.llm_clients import get_chat_llm
from langchain.messages import SystemMessage, HumanMessage
from backend.config.prompts import RAG_SYSTEM_PROMPT


def build_context(relevant_chunks: list[dict], web_results: list[dict]) ->str:
    parts= []
    for c in relevant_chunks:
        page_suffix= f" p.{c['page']}" if c.get("page") else ""
        parts.append(f"[Source: {c['source']}{page_suffix}]\n{c['text']}")
    for r in web_results:
        parts.append(f"[Source: {r['title']} ({r['url']})]\n{r['content']}")
    return "\n\n".join(parts)


def run_rag_agent(state:AgentState):
    query= state["user_query"]
    # expantions= expand_query(query=query)
    # state['expanded_queries']= expantions

    # all_candidates= {}
    # for q in expantions:
    #     for chunk in retrieve(q, top_k=RETRIEVAL_TOP_K):
    #         all_candidates[chunk["chunk_id"]]= chunk

    all_candidates= {}
    for chunk in retrieve(query, top_k=RETRIEVAL_TOP_K):
        all_candidates[chunk["chunk_id"]]= chunk

    reranked= rerank(query, list(all_candidates.values()), top_k= RERANKER_TOP_K)

    if not reranked:
        logger.info("No chunks retrieved from knowledge base -> handing off to web_search")
        state["route"]= "web_search_handoff"
        state['rag_confidence']= 0.0
        return state

    relevant, irrelavant= check_relevance(query, reranked)
    state["relevant_chunks"]= relevant
    state['irrelevant_chunks']= irrelavant

    if not relevant:
        logger.info("All retrieved chunks judged irrelevant -> handing off to web_search")
        state["route"]= "web_search_handoff"
        state['rag_confidence']= 0.0
        return state

    web_supplement=[]
    if irrelavant:
        try:
            web_supplement= search_medical_web(query, max_results=len(irrelavant))
            logger.info(f"Backfilled {len(web_supplement)} web result (s) for {len(irrelavant)} irrelevant chunks(s)")
        except Exception as e:
            logger.warning(f"Web backfill for irrelevant chunks failed, continuing with RAG-ONLY context: {e}")

    state['web_supplement_results']= web_supplement

    context= build_context(relevant, web_supplement)

    llm= get_chat_llm(temperature=0.1)
    resp= llm.invoke([
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
    ])
    raw= resp.content
    answer, confidence= extract_confidence(raw)
    top_reranker_score= relevant[0].get("rerank_score")
    normalized_rerank= max(0.0, min(1.0, (top_reranker_score +10)/20))
    blended= round(0.6 * confidence + 0.4 * normalized_rerank, 3)

    state['rag_answer']= answer
    state['rag_confidence']= blended
    logger.info(f"RAG agent confidence= {blended} (llm={confidence}, rerank_norm={normalized_rerank})")

    return state


def extract_confidence(raw_text:str) -> tuple[str, float]:
    lines= raw_text.strip().splitlines()
    confidence=0.5
    answer_lines= []

    for line in lines:
        if line.strip().upper().startswith("CONFIDENCE:"):
            try:
                confidence= float(line.split(":",1)[1].strip())
            except ValueError:
                pass
        else:
            answer_lines.append(line)

    return "\n".join(answer_lines).strip(), max(0.0, min(1.0, confidence))
