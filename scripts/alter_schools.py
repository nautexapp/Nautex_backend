import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal, init_db

async def add_cols():
    init_db()
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(text("ALTER TABLE schools ADD COLUMN info JSONB"))
            print("Column 'info' added to 'schools' table.")
        except Exception as e:
            print("Column may already exist:", e)
        await db.commit()

if __name__ == "__main__":
    asyncio.run(add_cols())
