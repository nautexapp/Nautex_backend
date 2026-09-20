import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.core.identity import AuthenticatedUser

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_jwks_client: PyJWKClient | None = None


def _get_google_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)
    return _jwks_client


def _decode_google_token(token: str, settings: Settings) -> dict:
    """
    Decodifica y valida un ID Token emitido por Google Identity Services.
    En modo depuración (DEBUG=true), permite tokens de prueba mockeados.
    """
    if settings.debug and token in ("dev-token", "test-token"):
        return {
            "sub": "google-mock-test-id",
            "email": "test@nautex.es",
            "name": "Usuario Pruebas",
        }

    try:
        jwks_client = _get_google_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        decode_kwargs = {
            "algorithms": ["RS256"],
            "options": {"verify_exp": True},
        }
        if settings.google_client_id:
            decode_kwargs["audience"] = settings.google_client_id
        else:
            decode_kwargs["options"]["verify_aud"] = False

        claims = jwt.decode(token, signing_key.key, **decode_kwargs)

        issuer = claims.get("iss")
        if issuer not in ("accounts.google.com", "https://accounts.google.com"):
            raise jwt.InvalidIssuerError(f"Issuer de Google no reconocido: {issuer}")

        return claims
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión ha caducado. Inicia sesión de nuevo.",
        ) from exc
    except Exception as exc:
        logger.warning("Token de Google inválido: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no válido o no autenticado con Google",
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

    claims = _decode_google_token(credentials.credentials, settings)

    google_id = claims.get("sub")
    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no incluye el identificador de usuario (sub)",
        )

    email = claims.get("email")
    if not email or not isinstance(email, str) or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no incluye un email válido",
        )

    return AuthenticatedUser(google_id=str(google_id), email=email.lower())
