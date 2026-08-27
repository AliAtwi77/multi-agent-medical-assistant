#imaging_router.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from backend.api.database.database import get_db
from backend.api.models import db_models as m
from backend.api.models.schemas import ImageAnalysisResponse
from backend.config.prompts import IMAGE_ANALYSIS_DEFAULT_PROMPT
import os
from backend.guardrails.input_guardrail import check_input_guardrail
from backend.utils.conversation_helpers import get_or_create_conversation, filepath_to_media_url
from backend.config.settings import UPLOAD_DIR
import uuid
from backend.agentic_system.state import AgentState
from backend.agentic_system.agents.imaging_analysis_agent import run_image_analysis_agent
from backend.utils.exceptions import MedicalAssistantError
from backend.utils.logger import logger


router= APIRouter(
    prefix="/api/imaging",
    tags=["imaging"],
)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".dcm", ".tiff", ".bmp"}

@router.post("/upload", response_model=ImageAnalysisResponse)
async def upload_and_analyze_image(
    file: UploadFile = File(...),
    prompt: str = Form(IMAGE_ANALYSIS_DEFAULT_PROMPT),
    conversation_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported image type '{ext}'.")

    passed, reason = check_input_guardrail(prompt)
    if not passed:
        raise HTTPException(status_code=422, detail=f"Request blocked by safety guardrail: {reason}")

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        image_id = str(uuid.uuid4())
        filepath = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)

        doc_record = m.DocumentRecord(
            id=image_id, filename=file.filename or "image", filepath=filepath,
            num_chunks=0, status="ready",
        )
        db.add(doc_record)
        db.commit()

        image_url = filepath_to_media_url(filepath)

        conversation = get_or_create_conversation(db, conversation_id, prompt)

        user_msg = m.Message(
            conversation_id=conversation.id, role="user", content=prompt, image_url=image_url,
        )
        db.add(user_msg)
        db.commit()

        state: AgentState = {"user_query": prompt, "image_id": image_id, "chat_history": []}
        state = run_image_analysis_agent(state, filepath)

        findings = state.get(
            "image_findings",
            "Image analysis did not return a result. Please have a qualified "
            "radiologist/clinician review the image directly.",
        )
        confidence = state.get("image_confidence", 0.0)

        assistant_msg = m.Message(
            conversation_id=conversation.id,
            role="assistant",
            content=findings,
            agent_used="image_analysis",
            confidence=confidence,
            needs_human_review=True,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return ImageAnalysisResponse(
            image_id=image_id,
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            image_url=image_url,
            findings=findings,
            confidence=confidence,
            needs_human_review=True,
        )
    except MedicalAssistantError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image upload/analysis failed")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")