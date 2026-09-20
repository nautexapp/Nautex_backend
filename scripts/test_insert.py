import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal, init_db
from app.db.models import User
from app.core.identity import AuthenticatedUser
from app.services.users import sync_user

async def test():
    init_db()
    async with AsyncSessionLocal() as session:
        identity = AuthenticatedUser(entra_id="12345", email="test@test.com")
        try:
            user, created = await sync_user(session, identity)
            await session.commit()
            print("SUCCESS! User ID:", user.id)
        except Exception as e:
            print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(test())
