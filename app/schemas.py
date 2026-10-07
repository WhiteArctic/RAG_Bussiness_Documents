"""Schemas Pydantic: el contrato de entrada/salida de la API.

FastAPI usa estas clases para:
- Validar automáticamente el request (rechaza datos inválidos con HTTP 422).
- Serializar la respuesta a JSON.
- Generar la documentación OpenAPI (/docs) sin esfuerzo extra.
"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Lo que el cliente envía al endpoint /ask."""

    question: str = Field(
        ...,  # obligatorio
        min_length=3,
        max_length=2000,
        description="Pregunta del usuario sobre los documentos.",
    )


class AskResponse(BaseModel):
    """Lo que la API devuelve."""

    answer: str = Field(..., description="Respuesta generada por el LLM.")
    model: str = Field(..., description="Modelo usado para generar la respuesta.")
    sources: list[str] = Field(
        default_factory=list,
        description="Documentos fuente usados para responder (trazabilidad/citas).",
    )
