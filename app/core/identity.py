from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    entra_id: str
    email: str
