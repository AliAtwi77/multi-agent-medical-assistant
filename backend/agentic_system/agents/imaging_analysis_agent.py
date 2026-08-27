#imaging_analysis_Agent.py
from backend.agentic_system.state import AgentState
from backend.config.prompts import IMAGE_ANALYSIS_DEFAULT_PROMPT
from backend.imaging.medgemma_client import analyze_image
from backend.utils.logger import logger

def run_image_analysis_agent(state:AgentState, image_path:str) -> AgentState:
    prompt= state["user_query"] or IMAGE_ANALYSIS_DEFAULT_PROMPT
    try:
        result= analyze_image(image_path, prompt)
        state["image_findings"]= result['findings']
        state["image_confidence"]=result['confidence']
        logger.info(f"Image analysis confidence= {result['confidence']}")
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        state["image_findings"]= (
            "Image analysis could not be completed automatically."
            "Please have a qualified radiologist/clinician review the image directly."
        )
        state["image_confidence"]=0.0
    return state

