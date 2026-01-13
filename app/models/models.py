"""
Example Database Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Application(Base):
    """Application model for bexio marketplace apps"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    short_description = Column(Text, nullable=True)
    link = Column(String, nullable=False)
    image = Column(String, nullable=True)
    price = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Application {self.name}>"


class AppTag(Base):
    """App tags model for categories and industries"""
    __tablename__ = "apps_tags"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AppTag app_id={self.app_id} tag={self.tag}>"
