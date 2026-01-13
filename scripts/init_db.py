"""
Database Initialization Script

Run this script to create all tables in the database.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_db, engine
from app.models.models import Application, AppTag, Card, CardPrompt  # Import all models


async def main():
    """Initialize database tables"""
    print("🔧 Creating database tables...")
    await init_db()
    print("✅ Database tables created successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
