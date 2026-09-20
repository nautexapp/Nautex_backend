from pydantic import BaseModel, Field


class CheckoutSessionRequest(BaseModel):
    pack_id: str = Field(
        default="credits_50",
        description="Identificador del pack (p. ej. credits_50)",
    )


class CheckoutSessionResponse(BaseModel):
    payment_url: str
    order_id: str
    payment_id: str | None = None


class WebhookAckResponse(BaseModel):
    received: bool = True
