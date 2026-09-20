import logging
import urllib.parse
from app.config import Settings

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3_client(settings: Settings):
    global _s3_client
    if _s3_client is None:
        import boto3
        from botocore.config import Config

        endpoint = settings.effective_r2_endpoint
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint if endpoint else None,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _s3_client


def generate_academy_read_sas(
    settings: Settings,
    *,
    blob_path: str,
) -> str:
    """
    Genera una URL temporal presignada de Cloudflare R2 o una URL pública directa
    para un archivo estático del curso (tests, apuntes, exámenes, documentos).

    blob_path: ruta relativa del objeto, ej. "pnb/Tests/1. Nomenclatura nautica.json"
    """
    # Normalizar ruta eliminando barras iniciales
    key = blob_path.lstrip("/")

    # 1. Si el bucket tiene acceso público habilitado (ej: dominio propio o *.r2.dev)
    if settings.r2_public_url:
        base_url = settings.r2_public_url.rstrip("/")
        # Codificar de forma segura respetando las barras del path
        encoded_key = "/".join(urllib.parse.quote(part) for part in key.split("/"))
        return f"{base_url}/{encoded_key}"

    # 2. Si hay credenciales de Cloudflare R2 configuradas, generar URL presignada S3v4
    if settings.r2_access_key_id and settings.r2_secret_access_key:
        try:
            s3 = _get_s3_client(settings)
            expires_seconds = settings.academy_sas_expiry_minutes * 60
            url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.r2_bucket_name,
                    "Key": key,
                },
                ExpiresIn=expires_seconds,
            )
            return url
        except Exception as exc:
            logger.error("Error generando URL presignada de Cloudflare R2: %s", exc)

    # 3. Fallback de desarrollo local si no hay credenciales R2 todavía
    logger.warning("R2 no configurado. Devolviendo ruta simulada para: %s", key)
    return f"/mock-storage/{key}"
