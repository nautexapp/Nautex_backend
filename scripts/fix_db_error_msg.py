import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

async def fix_existing_materials():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE materials ADD COLUMN error_message VARCHAR;"))
            print("Columna añadida correctamente.")
        except Exception as e:
            print(f"Error al añadir columna: {e}")
    await engine.dispose()

asyncio.run(fix_existing_materials())
