#conversation_helpers.py
from sqlalchemy.orm import Session
from backend.api.models import db_models as m
import os
from backend.config.settings import UPLOAD_DIR

def get_or_create_conversation(db:Session, conversation_id:str | None, first_message:str) -> m.Conversation:
    if conversation_id:
        conv= db.query(m.Conversation).filter(m.Conversation.id == conversation_id).first()
        if conv:
            return conv
    title= (first_message[:60] + "...") if len(first_message) > 60 else first_message
    conv= m.Conversation(title=title or "New conversation")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv
 
 
def filepath_to_media_url(filepath: str) -> str:
    """
    Converts an absolute on-disk path under UPLOAD_DIR into the
    servable URL exposed by the /media static mount in main.py, e.g.
    "./data/uploads/abc123.png" -> "/media/abc123.png"
    """
    rel_path = os.path.relpath(filepath, UPLOAD_DIR)
    return f"/media/{rel_path.replace(os.sep, '/')}"
 