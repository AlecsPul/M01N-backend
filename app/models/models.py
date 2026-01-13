"""
Example Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
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


    def __repr__(self):
        return f"<Application {self.name}>"


class AppTag(Base):
    """App tags model for categories and industries"""
    __tablename__ = "apps_tags"

    id = Column(String, primary_key=True, index=True)
    app_id = Column(String, ForeignKey("application.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AppTag app_id={self.app_id} tag={self.tag}>"
