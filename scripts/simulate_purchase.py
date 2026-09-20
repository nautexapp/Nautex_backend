"""
Simula la compra de un paquete para un usuario dado su email.
Uso:
    python scripts/simulate_purchase.py --email tu@email.com --package per
"""
import asyncio
import argparse
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import User, UserPackage, AcademyPackage

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


async def simulate_purchase(email: str, package_id: str):
    from app.db.session import init_db
    init_db()
    async with AsyncSessionLocal() as db:
        # Buscar usuario
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌  No se encontró ningún usuario con email '{email}'.")
            print("    Usuarios disponibles:")
            all_users = await db.execute(select(User.email, User.id))
            for row in all_users.all():
                print(f"      · {row.email}  ({row.id})")
            return

        # Buscar paquete
        result = await db.execute(select(AcademyPackage).where(AcademyPackage.id == package_id))
        package = result.scalar_one_or_none()
        if not package:
            print(f"❌  No se encontró el paquete '{package_id}'.")
            result = await db.execute(select(AcademyPackage.id, AcademyPackage.title))
            print("    Paquetes disponibles:")
            for row in result.all():
                print(f"      · {row.id}  —  {row.title}")
            return

        # Comprobar si ya está comprado
        result = await db.execute(
            select(UserPackage).where(
                UserPackage.user_id == user.id,
                UserPackage.package_id == package_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"ℹ️   El usuario '{email}' ya tiene el paquete '{package_id}'.")
            return

        # Insertar compra
        purchase = UserPackage(
            user_id=user.id,
            package_id=package_id,
        )
        db.add(purchase)
        await db.commit()
        print(f"✅  Compra simulada correctamente.")
        print(f"    Usuario : {email}")
        print(f"    Paquete : [{package_id}] {package.title}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simula la compra de un paquete.")
    parser.add_argument("--email",   required=True, help="Email del usuario")
    parser.add_argument("--package", required=True, help="ID del paquete (ej: per, patron-yate)")
    args = parser.parse_args()

    asyncio.run(simulate_purchase(args.email, args.package))
