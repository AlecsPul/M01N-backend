"""
Database Initialization Script

Run this script to create all tables in the database.
"""
import asyncio
from app.database import init_db, engine
from app.models.models import User, Item  # Import all models


async def main():
    """Initialize database tables"""
    print("🔧 Creating database tables...")
    await init_db()
    print("✅ Database tables created successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
