from dotenv import load_dotenv
import os
from backend.utils.exceptions import WebSearchError
from exa_py import Exa
from backend.config.settings import EXA_MAX_SEARCH_RESULTS
from backend.web_search.domains_to_search import MEDICAL_WEB_SEARCH_DOMAINS

def get_client():
    EXA_API_KEY=os.getenv("EXA_API_KEY")
    if not EXA_API_KEY:
        raise WebSearchError("EXA_API_KEY is not configured.")
    client= Exa(api_key=EXA_API_KEY)
    return client

def search_medical_web(query:str, max_results:int= EXA_MAX_SEARCH_RESULTS)->list[dict]:
    """Returns list of {'title', 'url', 'content', 'score'}"""
    try:
        client=get_client()
        response= client.search(
            query,
            type="auto",
            num_results= max_results,
            include_domains= MEDICAL_WEB_SEARCH_DOMAINS,
            contents={"text": True}
        )
        hits= response.results

        if not hits:
            response= client.search(query, type="auto", num_results=max_results, contents={'text':True})
            hits= response.results

        return [
            {
                "title": r.title or "",
                "url": r.url or "",
                "content":r.text or "",
                "score": r.score if r.score is not None else 0.0,
            }
            for r in hits
        ]
    except WebSearchError:
        raise
    except Exception as e:
        raise WebSearchError(f"EXA web search failed: {e}") from e

