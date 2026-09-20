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

    app_name: str = "ExamIA API"
    debug: bool = False
    api_prefix: str = "/api"

    cors_origins: list[str] = Field(
        default=["https://localhost:5173", "http://localhost:5173", "http://127.0.0.1:5173"]
    )

    database_url_secret_name: str = "database-url"
    database_url: str = Field(
        default="postgresql+asyncpg://admin_local:superpassword123@localhost:5432/nautex_db"
    )

    azure_tenant_id: str = ""
    azure_client_id: str = ""
    entra_client_id: str = ""
    azure_audience: str | None = None
    # Para tenants CIAM con subdominio personalizado (e.g. "examiapp")
    azure_tenant_name: str = ""
    azure_auth_type: str = "entra"  # entra | ciam

    azure_key_vault_url: str = ""
    storage_connection_secret_name: str = "storage-connection-string"
    # Para desarrollo local sin Key Vault: pon la connection string directamente aquí
    storage_connection_string: str = ""
    storage_container_name: str = "uploads"
    storage_generations_container_name: str = "generations"
    storage_academy_container_name: str = "cursos"
    upload_sas_expiry_minutes: int = 5
    academy_sas_expiry_minutes: int = 30

    monei_api_key_secret_name: str = "monei-api-key"
    monei_api_key: str = ""
    monei_webhook_url: str = ""
    payment_complete_url: str = "http://localhost:5173/pago/completado"
    payment_cancel_url: str = "http://localhost:5173/pago/cancelado"

    ai_api_key_secret_name: str = "ai-api-key"
    ai_api_key: str = ""
    ai_model: str = "deepseek-v4-flash"
    ai_base_url: str = "https://api.deepseek.com/v1"

    @property
    def azure_issuer(self) -> str:
        if self.azure_auth_type == "ciam" and self.azure_tenant_id:
            # El issuer real de CIAM usa el tenantId como subdominio (no el tenant name)
            return f"https://{self.azure_tenant_id}.ciamlogin.com/{self.azure_tenant_id}/v2.0"
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}/v2.0"

    @property
    def azure_jwks_url(self) -> str:
        if self.azure_auth_type == "ciam" and self.azure_tenant_name:
            # Usamos el tenant name (examiapp) para la discovery, pero el issuer usa el UUID
            return (
                f"https://{self.azure_tenant_name}.ciamlogin.com"
                f"/{self.azure_tenant_id}/v2.0/.well-known/openid-configuration"
            )
        return (
            f"https://login.microsoftonline.com/{self.azure_tenant_id}"
            "/v2.0/.well-known/openid-configuration"
        )

    @property
    def token_audiences(self) -> list[str]:
        # Si no hay audience manual, usar el client_id como audience por defecto
        # (formato normal y formato api://)
        audiences = []
        if self.azure_audience:
            audiences.append(self.azure_audience)
        if self.azure_client_id:
            audiences.append(self.azure_client_id)
            audiences.append(f"api://{self.azure_client_id}")
        if self.entra_client_id:
            audiences.append(self.entra_client_id)
            audiences.append(f"api://{self.entra_client_id}")

        return list(dict.fromkeys(audiences))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Limpia la caché de configuración. Llamar en el startup del servidor."""
    get_settings.cache_clear()
