"""
Example Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class Application(Base):
    """Application model for bexio marketplace apps"""
    __tablename__ = "application"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    price_text = Column(String, nullable=True)
    
    # Relationship to tags
    tags = relationship("AppTag", back_populates="application", lazy="selectin")

    def __repr__(self):
        return f"<Application {self.name}>"


class AppTag(Base):
    """App tags model for categories and industries"""
    __tablename__ = "apps_tags"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("application.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to application
    application = relationship("Application", back_populates="tags")

    def __repr__(self):
        return f"<AppTag app_id={self.app_id} tag={self.tag}>"

class Card(Base):
    """Card model for user requests"""
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Integer, default=0, nullable=False)  # 0 or 1
    number_of_requests = Column(Integer, default=0, nullable=False)
    upvote = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Card {self.title} (status={self.status})>"


class CardPromptComment(Base):
    """Card prompts and comments model"""
    __tablename__ = "card_prompts_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    comment_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CardPrompt {self.id} for Card {self.card_id}>"