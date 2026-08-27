from dotenv import load_dotenv
import os
from langchain_anthropic import ChatAnthropic
from backend.config.settings import CHAT_MODEL, SMALL_MODEL

load_dotenv()
ANTHROPIC_API_KEY= os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY= os.getenv('OPENAI_API_KEY')

def get_chat_llm(temperature:float =0.2, ):
    """Main conversational/reasoning LLM, used by the router, RAG, websearch, and general-chat agents"""
    if ANTHROPIC_API_KEY:
        return ChatAnthropic(
            model=CHAT_MODEL,
            temperature=temperature,
            api_key=ANTHROPIC_API_KEY
        )
    raise RuntimeError("No Anthropic API key configure")

def get_small_llm():
    """Small LLM dedicated to guardrail classification, relevance checking, and query expansion"""
    if ANTHROPIC_API_KEY:
        return ChatAnthropic(
            model=SMALL_MODEL,
            temperature=0,
            api_key=ANTHROPIC_API_KEY
        )
    raise RuntimeError("No Anthropic API key configure")