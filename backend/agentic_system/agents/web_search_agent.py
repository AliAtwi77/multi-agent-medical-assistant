from backend.agentic_system.state import AgentState
from backend.web_search.exa_client import search_medical_web
from backend.utils.logger import logger
from backend.config.llm_clients import get_chat_llm
from langchain.messages import SystemMessage, HumanMessage
from backend.config.prompts import WEB_SEARCH_SYSTEM_PROMPT

def run_web_search_agent(state:AgentState) -> AgentState:
    query= state["user_query"]
    try:
        results= search_medical_web(query)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        state['web_results']= []
        state["web_answer"] = "Web search is currently unavailable."
        state["web_confidence"] = 0.0

        return state

    state['web_results']= results
    if not results:
        state['web_answer']="No current web results were found for this query."
        state["web_confidence"]= 0.0
        return state

    context= "\n\n".join(f"[Source: {r['title']} ({r['url']})]\n{r['content']}" for r in results)

    llm=get_chat_llm(temperature=0.1)
    resp = llm.invoke([
        SystemMessage(content=WEB_SEARCH_SYSTEM_PROMPT),
        HumanMessage(content=f"Search results:\n{context}\n\nQuestion: {query}")
    ])
    raw= resp.content if isinstance(resp.content, str) else str(resp.content)

    answer, confidence= extract_confidence(raw)
    state["web_answer"]= answer
    state["web_confidence"]= confidence
    logger.info(f"Web search Agent confidence= {confidence}")

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