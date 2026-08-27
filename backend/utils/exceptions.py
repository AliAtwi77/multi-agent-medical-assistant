class MedicalAssistantError(Exception):
    status_code= 500

    def __init__(self, message:str, details:dict | None= None):
        super().__init__(message)
        self.message= message
        self.details= details or {}


class RetrievalError(MedicalAssistantError):
    """Raised when the rag pipeline fails to retrieve or embed data"""
    status_code= 502

class VoiceProcessingError(MedicalAssistantError):
    """Raised when STT/TTS calls to ElevenLabs fail"""
    status_code=502

class GuardrailViolationError(MedicalAssistantError):
    """Raised wjen input/output guardrails black a request/response"""
    status_code=422


class ImageAnalysisError(MedicalAssistantError):
    """Raised when MedGEMMA image analysis fails"""
    status_code=502

class WebSearchError(MedicalAssistantError):
    """Raised when Tavily web search fails"""
    status_code=502

class OrchestrationError(MedicalAssistantError):
    """Raised when the Langgraph agent workflow fails unexpectedly"""
    status_code=500