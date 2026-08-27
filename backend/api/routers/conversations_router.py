from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.database.database import get_db
from backend.api.models import db_models as m
from backend.api.models.schemas import ReviewDecision
from backend.utils.logger import logger

router = APIRouter(prefix="/api", tags=["conversations"])


@router.get("/conversations")
def list_conversations(db: Session= Depends(get_db)):
    convs= db.query(m.Conversation).order_by(m.Conversation.created_at.desc()).all()
    return [{'id': c.id, "title":c.title, "created_at":c.created_at.isoformat()} for c in convs]


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id:str, db: Session= Depends(get_db)):
    conv= db.query(m.Conversation).filter(m.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not Found")
    messages= sorted(conv.messages, key= lambda x: x.created_at)

    return [
        {
            "id": msg.id, "role": msg.role, "content": msg.content,
            "agent_used": msg.agent_used, "confidence": msg.confidence,
            "sources": msg.sources, "needs_human_review": msg.needs_human_review,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.get("/reviews/pending")
def list_pending_reviews(db: Session = Depends(get_db)):
    messages = db.query(m.Message).filter(m.Message.needs_human_review == True).all()  # noqa: E712
    return [
        {"message_id": msg.id, "conversation_id": msg.conversation_id, "content": msg.content,
         "agent_used": msg.agent_used, "confidence": msg.confidence, "created_at": msg.created_at.isoformat()}
        for msg in messages
    ]


@router.post("/reviews/decision")
def submit_review_decision(payload: ReviewDecision, db: Session = Depends(get_db)):
    msg = db.query(m.Message).filter(m.Message.id == payload.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found.")

    review = m.HumanReview(
        message_id=payload.message_id,
        reviewer_name=payload.reviewer_name,
        decision=payload.decision,
        corrected_content=payload.corrected_content or "",
        notes=payload.notes or "",
    )
    db.add(review)

    if payload.decision in ("approved", "edited"):
        msg.needs_human_review = False
        if payload.decision == "edited" and payload.corrected_content:
            msg.content = payload.corrected_content

    db.commit()
    logger.info(f"Human review recorded for message {payload.message_id}: {payload.decision}")
    return {"status": "recorded"}
