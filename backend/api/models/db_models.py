import uuid 
from backend.api.database.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, Float, DateTime, ForeignKey, JSON
import datetime as dt
from datetime import UTC

def _uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, default="New conversation")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now(dt.UTC))

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    agent_used: Mapped[str] = mapped_column(String, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sources: Mapped[dict] = mapped_column(JSON, default=dict)
    image_url: Mapped[str] = mapped_column(String, default="")  # servable /media/... path, if this message had an attached image
    needs_human_review: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now(dt.UTC))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String)
    num_chunks: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String, default="processing")  # processing | ready | failed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now(dt.UTC))


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    reviewer_name: Mapped[str] = mapped_column(String, default="")
    decision: Mapped[str] = mapped_column(String, default="pending")  # pending | approved | rejected | edited
    corrected_content: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.now(dt.UTC))
