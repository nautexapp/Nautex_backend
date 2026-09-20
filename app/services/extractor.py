"""
Extractor de texto de documentos.
Soporta:
  - PDF  (MIME: application/pdf)            → PyMuPDF
  - DOCX (MIME: application/vnd.openxmlformats-officedocument.wordprocessingml.document) → python-docx

El archivo se descarga de Azure Blob Storage a memoria y nunca se escribe en disco.
"""

import io
import logging

from docx import Document as DocxDocument
from app.config import Settings

logger = logging.getLogger(__name__)

def _download_blob_to_bytes(settings: Settings, blob_name: str) -> bytes:
    """Descarga un archivo desde Cloudflare R2 a memoria."""
    from app.services.storage import _get_s3_client
    s3 = _get_s3_client(settings)
    response = s3.get_object(Bucket=settings.r2_bucket_name, Key=blob_name)
    return response["Body"].read()


def _extract_from_pdf(data: bytes) -> str:
    """
    Extrae el texto de un PDF usando pymupdf4llm.
    Respeta el orden visual del layout (columnas, tablas, etc.).

    Los imports son lazy (dentro de la función) para que el modelo ONNX
    de pymupdf_layout NO se cargue al arrancar el contenedor, sino solo
    cuando se ejecuta la primera extracción en el hilo background.
    """
    import fitz
    import pymupdf4llm

    doc = fitz.open(stream=data, filetype="pdf")
    md_text = pymupdf4llm.to_markdown(doc)
    doc.close()
    return md_text


def _extract_from_docx(data: bytes) -> str:
    """Extrae el texto de un DOCX usando python-docx."""
    doc = DocxDocument(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(settings: Settings, blob_name: str, mime_type: str) -> str:
    """
    Descarga el blob de Azure y extrae su texto según el MIME type.

    Args:
        settings: Configuración de la aplicación.
        blob_name: Ruta del blob en Azure Storage.
        mime_type: MIME type del archivo (detectado al confirmar la subida).

    Returns:
        Texto extraído como string.

    Raises:
        ValueError: Si el MIME type no está soportado.
        RuntimeError: Si la descarga o extracción falla.
    """
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            f"Tipo de archivo no soportado: '{mime_type}'. "
            f"Solo se aceptan: {', '.join(SUPPORTED_MIME_TYPES)}"
        )

    logger.info(
        "Descargando blob '%s' (%s) para extracción de texto...",
        blob_name,
        MIME_LABEL.get(mime_type, mime_type),
    )

    data = _download_blob_to_bytes(settings, blob_name)

    if mime_type == "application/pdf":
        text = _extract_from_pdf(data)
    else:
        text = _extract_from_docx(data)

    char_count = len(text)
    logger.info("Extracción completada: %d caracteres extraídos de '%s'.", char_count, blob_name)

    if not text.strip():
        raise RuntimeError(
            "No se pudo extraer texto del documento. "
            "Es posible que el archivo esté escaneado o protegido."
        )

    return text
