import asyncio
import os
import sys

# Añadir el directorio base al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from sqlalchemy import text

async def add_column():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE user_packages ADD COLUMN tests_progress JSONB DEFAULT '{}'::jsonb NOT NULL;"))
            print("Columna tests_progress añadida correctamente a user_packages.")
        except Exception as e:
            print(f"La columna probablemente ya exista o hubo un error: {e}")

if __name__ == "__main__":
    asyncio.run(add_column())
