import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from app.db.session import AsyncSessionLocal, init_db
from app.db.models import User, School

async def check():
    init_db()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(School))
        schools = result.scalars().all()
        for s in schools:
            print(f"School {s.name}: id={s.id}")
            
        result = await db.execute(select(User))
        user = result.scalars().first()
        if user and schools:
            user.school_id = schools[0].id
            await db.commit()
            print("Assigned school to user!")

if __name__ == "__main__":
    asyncio.run(check())
