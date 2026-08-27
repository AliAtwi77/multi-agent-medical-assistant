#medgemma_client.py
import mimetypes
import base64
from  tenacity import retry, stop_after_attempt, wait_exponential
from backend.config.prompts import MEDGEMMA_SYSTEM_INSTRUCTION
from backend.config.settings import MEDGEMMA_MAX_TOKEN, MEDGEMMA_TEMPERATURE, MEDGEMMA_TOP_P, MEDGEMMA_BASE_URL
import httpx
from backend.utils.exceptions import ImageAnalysisError


def encode_image(image_path:str) -> tuple[str, str]:
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type= mime_type or "image/png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return b64, mime_type

@retry(stop= stop_after_attempt(3), wait= wait_exponential(multiplier=1, min=1, max=8))
def analyze_image(image_path:str, prompt:str) ->dict:
    try:
        image_64, mime_type= encode_image(image_path)

        payload= {
            "image_b64":image_64,
            "mime_type": mime_type,
            "prompt": f"{MEDGEMMA_SYSTEM_INSTRUCTION}\n\n{prompt}",
            "max_new_tokens":MEDGEMMA_MAX_TOKEN,
            "temperature": MEDGEMMA_TEMPERATURE,
            "top_p": MEDGEMMA_TOP_P,
        }
        headers= {}

        with httpx.Client(timeout=180.0) as client:
            resp= client.post(f"{MEDGEMMA_BASE_URL}/analyze", json= payload, headers= headers)
            resp.raise_for_status()
            data= resp.json()

        findings= data.get("text", "") or ""
        confidence = data.get("confidence")
        confidence = confidence if isinstance(confidence, (int, float)) else 0.5

        return {"findings": findings, "confidence": max(0.0, min(1.0, float(confidence)))}
    except Exception as e:
        raise ImageAnalysisError(f"MEDGEMMA image analysis failed: {e}") from e