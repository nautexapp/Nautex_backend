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
            await db.execute(text("ALTER TABLE materials ADD COLUMN correct_questions JSONB DEFAULT '[]'"))
        except Exception as e:
            print("correct_questions may already exist:", e)
        try:
            await db.execute(text("ALTER TABLE materials ADD COLUMN tests_completed INTEGER DEFAULT 0"))
        except Exception as e:
            print("tests_completed may already exist:", e)
        await db.commit()
        print('Cols added/verified!')

asyncio.run(add_cols())
