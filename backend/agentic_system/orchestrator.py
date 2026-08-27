#orchestrator
from backend.agentic_system.state import AgentState
from backend.guardrails.input_guardrail import check_input_guardrail
from backend.config.llm_clients import get_chat_llm
from langchain.messages import SystemMessage, HumanMessage, AIMessage
from backend.config.prompts import GENERAL_CHAT_SYSTEM_PROMPT, GUARDRAIL_BLOCKED_RESPONSE
from backend.agentic_system.agents.rag_agent import run_rag_agent
from backend.config.settings import CONFIDENCE_THRESHOLD
from backend.utils.logger import logger
from backend.agentic_system.agents.web_search_agent import run_web_search_agent
from backend.guardrails.output_guardrail import check_output_guardrail
from langgraph.graph import StateGraph, START, END
from backend.agentic_system.agents.router_agent import route_query
from backend.utils.exceptions import GuardrailViolationError, OrchestrationError


def input_guardrail_node(state:AgentState):
    passed, reason= check_input_guardrail(state['user_query'])
    state["guardrail_passed"] = passed
    state["guardrail_reason"] = reason
    if not passed:
        state["route"]= "blocked"
    return state


def general_node(state:AgentState):
    llm= get_chat_llm(temperature= 0.4)
    history_msgs= []
    for turn in state.get("chat_history", [])[-6:]:
        role= "assistant" if turn["role"] == "assistant" else "user"
        history_msgs.append((role, turn["content"]))

    messages= [SystemMessage(content= GENERAL_CHAT_SYSTEM_PROMPT)]
    for role, content in history_msgs:
        messages.append(HumanMessage(content=content) if role=="user" else AIMessage(content=content))
    messages.append(HumanMessage(content= state['user_query']))

    resp= llm.invoke(messages)
    state['final_answer']= resp.content if isinstance(resp.content, str) else str(resp.content)
    state['agent_used']= "general"
    state['confidence']=0.9
    state['sources']=[]
    return state


def rag_node(state:AgentState):
    state= run_rag_agent(state=state)
    if state["rag_confidence"] < CONFIDENCE_THRESHOLD:
        logger.info(
            f"RAG confidence {state['rag_confidence']} below threshold"
            f"{CONFIDENCE_THRESHOLD} -> handingg off to web_search"
        )
        state["route"]="web_search_handoff"
    return state


def web_search_node(state: AgentState):
    logger.info("Web SEARCH NODE")
    state= run_web_search_agent(state)
    return state


def finalize_node(state: AgentState) -> AgentState:
    """Merge whichever agent produced an answer into the final_answer field."""
    if state.get("route") in ("web_search", "web_search_handoff"):
        state["final_answer"] = state.get("web_answer", "")
        state["agent_used"] = "web_search" if state["route"] == "web_search" else "rag+web_search_handoff"
        state["confidence"] = state.get("web_confidence", 0.0)
        state["sources"] = [
            {"document": r["title"], "chunk_id": "", "snippet": r["content"][:220], "page": None}
            for r in state.get("web_results", [])
        ]
    elif state.get("route") == "rag":
        state["final_answer"] = state.get("rag_answer", "")
        agent_used = "rag"
        rag_sources = [
            {"document": c["source"], "chunk_id": c["chunk_id"], "page": c.get("page"),
             "snippet": c["text"][:220]}
            for c in state.get("relevant_chunks", [])
        ]
        web_backfill_sources = [
            {"document": r["title"], "chunk_id": "", "snippet": r["content"][:220], "page": None}
            for r in state.get("web_supplement_results", [])
        ]
        if web_backfill_sources:
            agent_used = "rag+web_backfill"
        state["agent_used"] = agent_used
        state["confidence"] = state.get("rag_confidence", 0.0)
        state["sources"] = rag_sources + web_backfill_sources
    # "general" node already set final_answer/agent_used/confidence directly
    return state

def output_guardrail_node(state: AgentState) -> AgentState:
    revised, needs_review, reason = check_output_guardrail(state.get("final_answer", ""))
    state["final_answer"] = revised
    state["needs_human_review"] = needs_review or state.get("confidence", 1.0) < CONFIDENCE_THRESHOLD
    state["guardrail_reason"] = reason
    return state


def blocked_node(state: AgentState) -> AgentState:
    state["final_answer"] = GUARDRAIL_BLOCKED_RESPONSE
    state["agent_used"] = "guardrail_blocked"
    state["confidence"] = 1.0
    state["needs_human_review"] = False
    state["sources"] = []
    return state


def _route_after_input_guardrail(state: AgentState) -> str:
    return "blocked" if not state.get("guardrail_passed", True) else "router"


def _route_after_router(state: AgentState) -> str:
    return state["route"]


def _route_after_rag(state: AgentState) -> str:
    return "web_search_handoff" if state.get("route") == "web_search_handoff" else "finalize"



def build_graph():
    graph=StateGraph(AgentState)

    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("router", route_query)
    graph.add_node("rag", rag_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("general", general_node)
    graph.add_node("blocked", blocked_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("output_guardrail", output_guardrail_node)

    graph.add_edge(START, "input_guardrail")

    graph.add_conditional_edges("input_guardrail", _route_after_input_guardrail, {"blocked": "blocked", "router": "router"})

    graph.add_conditional_edges("router", _route_after_router, {"rag": "rag", "web_search": "web_search", "general": "general"})

    graph.add_conditional_edges("rag",_route_after_rag, {"web_search_handoff": "web_search", "finalize": "finalize"})

    graph.add_edge("web_search", "finalize")
    graph.add_edge("general", "output_guardrail")
    graph.add_edge("finalize", "output_guardrail")
    graph.add_edge("blocked", END)
    graph.add_edge("output_guardrail", END)

    return graph.compile()

_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph

def run_workflow(user_query: str, conversation_id: str, chat_history: list[dict]) -> AgentState:
    try:
        graph = get_graph()
        initial_state: AgentState = {
            "conversation_id": conversation_id,
            "user_query": user_query,
            "chat_history": chat_history,
        }
        final_state = graph.invoke(initial_state)
        return final_state
    except GuardrailViolationError:
        raise
    except Exception as e:
        raise OrchestrationError(f"Agent workflow failed: {e}") from e