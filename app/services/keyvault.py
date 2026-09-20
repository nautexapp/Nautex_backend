import logging

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from app.config import Settings

logger = logging.getLogger(__name__)

import os

class SafeAzureCredential(DefaultAzureCredential):
    """
    Oculta temporalmente AZURE_CLIENT_ID del entorno durante la petición de token.
    Evita que azure-identity asuma que es una Identidad Administrada Asignada por el Usuario,
    lo que causaría un error 400 si esa variable contiene el ID de un App Registration.
    """
    def __init__(self, **kwargs):
        original_client_id = os.environ.pop("AZURE_CLIENT_ID", None)
        try:
            super().__init__(**kwargs)
        finally:
            if original_client_id is not None:
                os.environ["AZURE_CLIENT_ID"] = original_client_id

    def get_token(self, *scopes, **kwargs):
        original_client_id = os.environ.pop("AZURE_CLIENT_ID", None)
        try:
            return super().get_token(*scopes, **kwargs)
        finally:
            if original_client_id is not None:
                os.environ["AZURE_CLIENT_ID"] = original_client_id

_credential = SafeAzureCredential()
_secret_cache: dict[str, str] = {}


def get_secret(settings: Settings, secret_name: str) -> str:
    if not settings.azure_key_vault_url:
        raise RuntimeError("AZURE_KEY_VAULT_URL no está configurado")

    cache_key = f"{settings.azure_key_vault_url}:{secret_name}"
    if cache_key in _secret_cache:
        return _secret_cache[cache_key]

    client = SecretClient(vault_url=settings.azure_key_vault_url, credential=_credential)
    value = client.get_secret(secret_name).value
    if not value:
        raise RuntimeError(f"El secreto '{secret_name}' está vacío en Key Vault")

    _secret_cache[cache_key] = value
    logger.debug("Secreto '%s' cargado desde Key Vault", secret_name)
    return value
