from pydantic import BaseModel, Field
from backend.config.llm_clients import get_small_llm
from langchain.messages import SystemMessage, HumanMessage
from backend.config.prompts import INPUT_GUARDRAIL_SYSTEM_PROMPT
from backend.utils.logger import logger

class InputGuardrailVerdict(BaseModel):
    safe:bool= Field(description="True if the message is safe to process, false it it should be blocked.")
    reason: str= Field(description="One short sentence explaning the verdict")
    category:str=Field(description=" Short category label for the verdict, e.g. ' clinical_question', 'self_harm', 'off_topic', 'prompt_injection'.")


def check_input_guardrail(user_query:str) -> tuple[bool, str]:
    try:
        llm= get_small_llm().with_structured_output(InputGuardrailVerdict)
        verdict: InputGuardrailVerdict= llm.invoke([
            SystemMessage(content=INPUT_GUARDRAIL_SYSTEM_PROMPT),
            HumanMessage(content=user_query),
        ])

        if not verdict.safe:
            logger.warning(f"Input Guardrail BLOCKED query. Reason= {verdict.reason}")
        return verdict.safe, verdict.reason
    except Exception as e:
        logger.error(f"Input guarail error, defaulting to allow: {e}")
        return True, "guadrail_error_fallback"







