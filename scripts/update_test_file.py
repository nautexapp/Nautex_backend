import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.db.models import AcademyPackage
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AcademyPackage).where(AcademyPackage.id == "per"))
        pkg = result.scalar_one_or_none()
        if pkg:
            manifest = dict(pkg.content_manifest)
            # Añadimos un archivo de prueba al primer test
            if "tests" in manifest and len(manifest["tests"]) > 0:
                manifest["tests"][0]["file"] = "test-ripa.json"
                pkg.content_manifest = manifest
                await db.commit()
                print("Actualizado el paquete 'per'. El primer test ahora tiene file: 'test-ripa.json'")
            else:
                print("No se encontraron tests en el paquete 'per'")
        else:
            print("Paquete 'per' no encontrado")

if __name__ == "__main__":
    asyncio.run(main())
