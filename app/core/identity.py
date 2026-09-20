from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    google_id: str
    email: str

    @property
    def user_id(self) -> str:
        return self.google_id

    @property
    def entra_id(self) -> str:
        # Alias para compatibilidad
        return self.google_id
