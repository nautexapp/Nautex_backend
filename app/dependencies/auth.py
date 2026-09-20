import logging
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.core.identity import AuthenticatedUser

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client(settings: Settings) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        oidc_url = settings.azure_jwks_url
        with httpx.Client(timeout=10.0) as client:
            oidc = client.get(oidc_url)
            oidc.raise_for_status()
            jwks_uri = oidc.json()["jwks_uri"]
        _jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
    return _jwks_client


def _extract_email(claims: dict) -> str | None:
    # Entra ID estándar: preferred_username, email, upn, unique_name (string)
    for key in ("preferred_username", "email", "upn", "unique_name"):
        value = claims.get(key)
        if isinstance(value, str) and "@" in value:
            return value.lower()

    # Azure CIAM (External ID): el email viene en el array "emails"
    emails_array = claims.get("emails")
    if isinstance(emails_array, list):
        for entry in emails_array:
            if isinstance(entry, str) and "@" in entry:
                return entry.lower()

    return None


def _decode_entra_token(token: str, settings: Settings) -> dict:
    if not settings.azure_tenant_id or not settings.token_audiences:
        debug_info = f"tenant={bool(settings.azure_tenant_id)}, audiences={bool(settings.token_audiences)}, azure_client_id={bool(settings.azure_client_id)}, entra_client_id={bool(getattr(settings, 'entra_client_id', ''))}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Autenticación Entra ID no configurada en el servidor. Debug: {debug_info}",
        )

    try:
        jwks_client = _get_jwks_client(settings)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.token_audiences,
            issuer=settings.azure_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha caducado",
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Token inválido: %s | issuer esperado: %s | audiences: %s", exc, settings.azure_issuer, settings.token_audiences)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido",
        ) from exc


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere cabecera Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_entra_token(credentials.credentials, settings)

    entra_id = claims.get("oid") or claims.get("sub")
    if not entra_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no incluye identificador de usuario (oid/sub)",
        )

    email = _extract_email(claims)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no incluye un email válido",
        )

    return AuthenticatedUser(entra_id=str(entra_id), email=email)
