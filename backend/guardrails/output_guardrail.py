from pydantic import BaseModel, Field
from backend.config.llm_clients import get_small_llm
from langchain.messages import SystemMessage, HumanMessage
from backend.config.prompts import OUTPUT_GUARDRAIL_SYSTEM_PROMPT
from backend.utils.logger import logger


class OutputGuardrailVerdict(BaseModel):
    needs_review:bool=Field(description="True if a licensed clinical should review this answer before use.")
    reason:str = Field(description="One short sentence explanining the verdict.")
    revised_answer:str= Field(description="The answerm lightly edited if needed (e.g. softened diagnostic language). If no edit is needed, return the original answer unchanged.")


def check_output_guardrail(draft_answer:str)-> tuple[str, bool, str]:
    try:
        llm=get_small_llm().with_structured_output(OutputGuardrailVerdict)
        verdict: OutputGuardrailVerdict= llm.invoke([
            SystemMessage(content=OUTPUT_GUARDRAIL_SYSTEM_PROMPT),
            HumanMessage(content=draft_answer),
        ])
        revised= verdict.revised_answer or draft_answer
        return revised, verdict.needs_review, verdict.reason
    except Exception as e:
        logger.error(f"Output guardrail error, passing through draft unmodified: {e}")
        return draft_answer, True, "Guardrail_error_fallback_flagged_for_safety"