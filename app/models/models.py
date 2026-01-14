"""
Example Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
