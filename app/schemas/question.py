from pydantic import BaseModel, ConfigDict, Field


class QuestionAI(BaseModel):
    """Una pregunta tipo test generada por la IA (JSON minificado para ahorrar tokens)."""
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(alias="t")
    options: list[str] = Field(alias="o")
    correct_option: int = Field(default=1, alias="c", ge=1, le=4)
    explanation: str = Field(default="", alias="e")


class UsageStats(BaseModel):
    """Métricas de uso de tokens y coste del procesado de un documento."""
    chunks_processed: int
    input_tokens: int
    cached_tokens: int = 0
    output_tokens: int
    total_tokens: int
    cost_input_usd: float
    cost_output_usd: float
    cost_total_usd: float


class QuestionSetAI(BaseModel):
    """JSON completo guardado por documento: preguntas + métricas de uso."""
    questions: list[QuestionAI]
    usage: UsageStats | None = None
