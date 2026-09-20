import uuid
from datetime import datetime, timedelta, timezone

from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)

from app.config import Settings
from app.services.keyvault import get_secret


def _get_connection_string(settings: Settings) -> str:
    """Obtiene la cadena de conexión, priorizando la variable directa (para dev local)."""
    if settings.storage_connection_string:
        return settings.storage_connection_string
    if settings.azure_key_vault_url:
        return get_secret(settings, settings.storage_connection_secret_name)
    raise RuntimeError(
        "Configura STORAGE_CONNECTION_STRING en .env (dev) "
        "o AZURE_KEY_VAULT_URL + STORAGE_CONNECTION_SECRET_NAME (producción)"
    )


def _parse_connection_string(connection_string: str) -> tuple[str, str]:
    parts = dict(
        item.split("=", 1) for item in connection_string.split(";") if "=" in item
    )
    account_name = parts.get("AccountName")
    account_key = parts.get("AccountKey")
    if not account_name or not account_key:
        raise ValueError("La cadena de conexión de Storage no es válida")
    return account_name, account_key


def generate_upload_sas(
    settings: Settings,
    *,
    entra_id: str,
    filename: str,
) -> tuple[str, str, int]:
    connection_string = _get_connection_string(settings)
    account_name, account_key = _parse_connection_string(connection_string)

    safe_name = filename.replace("\\", "/").split("/")[-1] or "document.pdf"
    blob_name = f"users/{entra_id}/{uuid.uuid4()}_{safe_name}"

    import urllib.parse
    
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    expiry = datetime.now(timezone.utc) + timedelta(
        minutes=settings.upload_sas_expiry_minutes
    )

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.storage_container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(write=True, create=True, read=True, add=True),
        start=start_time,
        expiry=expiry,
    )

    upload_url = (
        f"https://{account_name}.blob.core.windows.net/"
        f"{settings.storage_container_name}/{urllib.parse.quote(blob_name)}?{sas_token}"
    )
    expires_seconds = settings.upload_sas_expiry_minutes * 60
    return upload_url, blob_name, expires_seconds


def blob_exists(settings: Settings, blob_name: str) -> bool:
    """Verifica si el blob existe en Azure Storage (para confirmar la subida)."""
    try:
        connection_string = _get_connection_string(settings)
        client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = client.get_blob_client(
            container=settings.storage_container_name, blob=blob_name
        )
        return blob_client.exists()
    except Exception:
        return False


def delete_blob(settings: Settings, blob_name: str, container_name: str | None = None) -> None:
    """Elimina un blob de Azure Storage de forma silenciosa."""
    container = container_name or settings.storage_container_name
    try:
        connection_string = _get_connection_string(settings)
        client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = client.get_blob_client(
            container=container, blob=blob_name
        )
        if blob_client.exists():
            blob_client.delete_blob()
    except Exception as exc:
        # En caso de error, lo logueamos pero no bloqueamos la eliminación de la BD
        print(f"Error borrando blob {blob_name}: {exc}")


def upload_json_to_blob(settings: Settings, blob_name: str, json_data: str) -> None:
    """Sube un string JSON directamente a Azure Blob Storage (sobrescribe si existe)."""
    connection_string = _get_connection_string(settings)
    client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = client.get_blob_client(
        container=settings.storage_generations_container_name, blob=blob_name
    )
    blob_client.upload_blob(json_data.encode("utf-8"), overwrite=True)


def upload_markdown_to_blob(settings: Settings, blob_name: str, md_data: str) -> None:
    """Sube un string Markdown directamente a Azure Blob Storage (sobrescribe si existe)."""
    connection_string = _get_connection_string(settings)
    client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = client.get_blob_client(
        container=settings.storage_generations_container_name, blob=blob_name
    )
    blob_client.upload_blob(md_data.encode("utf-8"), overwrite=True)


def get_blob_content(settings: Settings, blob_name: str) -> str:
    """Descarga el contenido de un blob de Azure Storage como string."""
    connection_string = _get_connection_string(settings)
    client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = client.get_blob_client(
        container=settings.storage_generations_container_name, blob=blob_name
    )
    if not blob_client.exists():
        raise FileNotFoundError(f"El blob {blob_name} no existe.")
    
    return blob_client.download_blob().readall().decode("utf-8")


def generate_academy_read_sas(
    settings: Settings,
    *,
    blob_path: str,
) -> str:
    """
    Genera una URL SAS de solo-lectura para un archivo del contenido de la Academia.
    blob_path: ruta dentro del contenedor, ej. "per/Apuntes/guia-ripa.pdf"
    """
    connection_string = _get_connection_string(settings)
    account_name, account_key = _parse_connection_string(connection_string)

    import urllib.parse
    
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    expiry = datetime.now(timezone.utc) + timedelta(
        minutes=settings.academy_sas_expiry_minutes
    )

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.storage_academy_container_name,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        start=start_time,
        expiry=expiry,
    )

    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{settings.storage_academy_container_name}/{urllib.parse.quote(blob_path)}?{sas_token}"
    )
