from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.models import db_models as m
from backend.utils.conversation_helpers import get_or_create_conversation, filepath_to_media_url
from backend.api.models.schemas import ChatResponse, ChatRequest, SourceRef
from backend.api.database.database import get_db
from backend.agentic_system.state import AgentState
from backend.agentic_system.agents.imaging_analysis_agent import run_image_analysis_agent
from backend.agentic_system.orchestrator import run_workflow
from backend.utils.exceptions import MedicalAssistantError
from backend.utils.logger import logger


router= APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        conversation = get_or_create_conversation(db, payload.conversation_id, payload.message)

        history = [
            {"role": msg.role, "content": msg.content}
            for msg in sorted(conversation.messages, key=lambda x: x.created_at)
        ]

        image_url = ""
        doc = None
        if payload.image_id:
            doc = db.query(m.DocumentRecord).filter(m.DocumentRecord.id == payload.image_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="Uploaded image not found.")
            image_url = filepath_to_media_url(doc.filepath)

        user_msg = m.Message(conversation_id=conversation.id, role="user", content=payload.message, image_url=image_url)
        db.add(user_msg)
        db.commit()

        if doc:
            state: AgentState = {
                "conversation_id": conversation.id,
                "user_query": payload.message,
                "image_id": payload.image_id,
                "chat_history": history,
            }
            state = run_image_analysis_agent(state, doc.filepath)
            answer = state.get(
                "image_findings",
                "Image analysis did not return a result. Please have a qualified "
                "radiologist/clinician review the image directly.",
            )
            confidence = state.get("image_confidence", 0.0)
            agent_used = "image_analysis"
            needs_review = True  # imaging findings ALWAYS require human sign-off
            sources = []
        else:
            final_state = run_workflow(payload.message, conversation.id, history)
            answer = final_state.get("final_answer", "")
            confidence = final_state.get("confidence", 0.0)
            agent_used = final_state.get("agent_used", "unknown")
            needs_review = final_state.get("needs_human_review", False)
            sources = final_state.get("sources", [])

        assistant_msg = m.Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            agent_used=agent_used,
            confidence=confidence,
            sources={"items": sources},
            needs_human_review=needs_review,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            answer=answer,
            agent_used=agent_used,
            confidence=confidence,
            needs_human_review=needs_review,
            sources=[SourceRef(**s) for s in sources],
        )
    except MedicalAssistantError as e:
        logger.error(f"Chat error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected chat error")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")