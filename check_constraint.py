import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check_constraint():
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT pg_get_constraintdef(oid) as definition "
            "FROM pg_constraint WHERE conname = 'cards_upvote_check'"
        ))
        row = result.fetchone()
        if row:
            print(f"Constraint definition: {row[0]}")
        else:
            print("Constraint not found")
        
        # También ver todas las columnas de la tabla cards
        result2 = await conn.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = 'cards' "
            "ORDER BY ordinal_position"
        ))
        print("\nCards table structure:")
        for row in result2:
            print(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")

asyncio.run(check_constraint())
