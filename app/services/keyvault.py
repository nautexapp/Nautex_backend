"""
Compatibilidad sin Azure Key Vault.
Los secretos se leen directamente de las variables de entorno / Settings.
"""

def get_secret(settings, secret_name: str) -> str:
    return ""
