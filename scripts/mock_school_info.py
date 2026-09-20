import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from app.db.session import AsyncSessionLocal, init_db
from app.db.models import School

async def mock_info():
    init_db()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(School))
        school = result.scalars().first()
        if school:
            school.info = {
                "phone": "600 123 456",
                "email": "contacto@nautica.com",
                "address": "Puerto Deportivo, Local 4",
                "website": "www.nautica.com",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Anchor_pictogram.svg/512px-Anchor_pictogram.svg.png"
            }
            await db.commit()
            print(f"Mock info added to school {school.name}")
        else:
            print("No schools found in DB.")

if __name__ == "__main__":
    asyncio.run(mock_info())
