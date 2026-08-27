# from pydantic import BaseModel, Field
# from backend.config.llm_clients import get_chat_llm
# from langchain.messages import SystemMessage, HumanMessage
# from backend.config.prompts import QUERY_EXPANSION_SYSTEM_PROMPT
# from backend.config.settings import QUERY_EXPANSION_MAX_VARIANTS
# from backend.utils.logger import logger


# class QueryExpansions(BaseModel):
#     expansions: list[str]= Field(description="2-3 alternative search phrasings using medical synonyms, abbreviations, or related clinical terms. Does not include the original query.")


# def expand_query(query:str)-> list[str]:
#     try:
#         llm= get_chat_llm(temperature=0.3).with_structured_output(QueryExpansions)
#         result: QueryExpansions = llm.invoke([
#             SystemMessage(content=QUERY_EXPANSION_SYSTEM_PROMPT),
#             HumanMessage(content=query)
#         ])
#         variants = [str(e) for e in result.expansions][:QUERY_EXPANSION_MAX_VARIANTS]

#         return [query] + variants

#     except Exception as e:
#         logger.warning(f"Query expansion failed, using original  query only: {e}")
#         return query


