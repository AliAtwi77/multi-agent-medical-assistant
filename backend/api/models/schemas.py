from pydantic import BaseModel, Field
from typing import Optional, Literal
from backend.config.prompts import IMAGE_ANALYSIS_DEFAULT_PROMPT

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    image_id: Optional[str] = None  # if user uploaded an image this turn


class SourceRef(BaseModel):
    document: str
    chunk_id: str
    page: Optional[int] = None
    snippet: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    agent_used: str
    confidence: float
    needs_human_review: bool
    sources: list[SourceRef] = Field(default_factory=list)


class ImageAnalysisRequest(BaseModel):
    prompt: str = IMAGE_ANALYSIS_DEFAULT_PROMPT


class ImageAnalysisResponse(BaseModel):
    image_id: str
    conversation_id: str
    message_id: str
    image_url: str
    findings: str
    confidence: float
    needs_human_review: bool
    disclaimer: str = (
        "This AI-generated analysis is not a diagnosis. "
        "It must be reviewed and confirmed by a licensed medical professional."
    )


class TTSRequest(BaseModel):
    text: str


class ReviewDecision(BaseModel):
    message_id: str
    reviewer_name: str
    decision: Literal["approved", "rejected", "edited"]
    corrected_content: Optional[str] = None
    notes: Optional[str] = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str