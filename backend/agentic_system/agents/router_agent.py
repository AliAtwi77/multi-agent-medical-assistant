from pydantic import BaseModel, Field
from typing import Literal
from backend.agentic_system.state import AgentState
from backend.config.llm_clients import get_chat_llm
from langchain.messages import SystemMessage, HumanMessage
from backend.config.prompts import ROUTER_SYSTEM_PROMPT
from backend.utils.logger import logger

class RouteDecision(AgentState):
    route: Literal['rag', 'web_search', 'general']= Field(description="The best next agent to handle this query.")
    reason:str= Field(description="One short sentence explaining the routing decision.")



def route_query(state:AgentState) ->AgentState:
    if state.get("image_id"):
        state["route"]= "image_analysis"
        return state

    try:
        llm = get_chat_llm(temperature=0).with_structured_output(RouteDecision)

        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]

        decision = llm.invoke(messages)

        if isinstance(decision, dict):
            decision = RouteDecision.model_validate(decision)

        if not isinstance(decision, RouteDecision):
            raise TypeError(f"Unexpected router response type: "f"{type(decision).__name__}")

        state["route"] = decision.route
        logger.info(f"Router selected route='{decision.route}' reason='{decision.reason}'")
    except Exception as e:
        logger.warning(f"Router LLM failed, defaulting to 'rag': {e}")
        state["route"]= "rag"

    return state



from typing import Literal

from pydantic import BaseModel, Field
from langchain.messages import SystemMessage, HumanMessage

from backend.agentic_system.state import AgentState
from backend.config.llm_clients import get_chat_llm
from backend.config.prompts import ROUTER_SYSTEM_PROMPT
from backend.utils.logger import logger


class RouteDecision(BaseModel):
    """Structured output returned by the router LLM."""

    route: Literal["rag", "web_search", "general"] = Field(
        description="The best next agent to handle this query."
    )

    reason: str = Field(
        description="One short sentence explaining the routing decision."
    )


def route_query(state: AgentState) -> AgentState:
    """
    Determine which agent should handle the user's query.

    Routes:
        - image_analysis: handled directly when an image_id is present
        - rag: retrieve information from the local knowledge base
        - web_search: search the web for current/external information
        - general: handle as a normal conversational request
    """

    # Image queries bypass the LLM router.
    if state.get("image_id"):
        state["route"] = "image_analysis"

        logger.info(
            "Image detected. Router selected route='image_analysis'"
        )

        return state

    try:
        llm = get_chat_llm(temperature=0).with_structured_output(
            RouteDecision
        )

        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]

        decision = llm.invoke(messages)

        # Some LangChain/LLM integrations return a dict even when
        # with_structured_output() is used.
        if isinstance(decision, dict):
            decision = RouteDecision.model_validate(decision)

        # Defensive validation in case a custom LLM integration returns
        # something unexpected.
        if not isinstance(decision, RouteDecision):
            raise TypeError(
                f"Unexpected router response type: "
                f"{type(decision).__name__}"
            )

        state["route"] = decision.route

        logger.info(
            "Router selected route='%s' reason='%s'",
            decision.route,
            decision.reason,
        )

    except Exception as e:
        # Keep the application running if the router LLM fails.
        # RAG remains the safest fallback for this application.
        logger.warning(
            "Router LLM failed, defaulting to 'rag': %s",
            e,
        )

        state["route"] = "rag"

    return state
