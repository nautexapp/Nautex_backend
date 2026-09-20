import os
from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nautex API"
    debug: bool = False
    api_prefix: str = "/api"

    cors_origins: list[str] = Field(
        default=[
            "https://localhost:5173",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://nautex-frontend.pages.dev",
        ]
    )

    # Base de Datos PostgreSQL
    database_url: str = Field(
        default="postgresql+asyncpg://admin_local:superpassword123@localhost:5432/nautex_db"
    )

    # Autenticación: Google OAuth 2.0 (Google Identity Services)
    google_client_id: str = ""

    # Almacenamiento: Cloudflare R2 (Compatible con S3)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "nautex-storage"
    r2_endpoint_url: str = ""
    r2_public_url: str = ""
    academy_sas_expiry_minutes: int = 60

    # Pasarela de Pagos MONEI
    monei_api_key: str = ""
    monei_webhook_url: str = ""
    payment_complete_url: str = "http://localhost:5173/pago/completado"
    payment_cancel_url: str = "http://localhost:5173/pago/cancelado"

    # Motor de IA (DeepSeek)
    ai_api_key: str = ""
    ai_model: str = "deepseek-v4-flash"
    ai_base_url: str = "https://api.deepseek.com/v1"

    @property
    def effective_r2_endpoint(self) -> str:
        if self.r2_endpoint_url:
            return self.r2_endpoint_url
        if self.r2_account_id:
            return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Limpia la caché de configuración. Llamar en el startup del servidor."""
    get_settings.cache_clear()
