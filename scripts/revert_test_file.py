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
            if "tests" in manifest and len(manifest["tests"]) > 0:
                if "file" in manifest["tests"][0]:
                    del manifest["tests"][0]["file"]
                    pkg.content_manifest = manifest
                    await db.commit()
                    print("Deshecho. El campo 'file' ha sido eliminado del primer test del paquete 'per'")
                else:
                    print("El campo 'file' ya no existe en ese test.")
            else:
                print("No se encontraron tests en el paquete 'per'")
        else:
            print("Paquete 'per' no encontrado")

if __name__ == "__main__":
    asyncio.run(main())
