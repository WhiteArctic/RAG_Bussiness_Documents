"""FastAPI app: la capa web que expone la funcionalidad vía HTTP."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.rag import build_index, answer_question
from app.llm import LLMUnavailableError
from app.schemas import AskRequest, AskResponse
from app.security import redact_pii
from app.config import settings

# Logging estructurado básico: en producción (Cloud Run) estos logs van a
# Cloud Logging. Registrar latencia/modelo/fuentes es la base de la
# observabilidad y del cálculo de costo por request (LLMOps, Día 2).
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

# Estado compartido de la app. El índice vive aquí, construido UNA vez.
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la app.

    INDEXACIÓN OFFLINE: construimos el vector store al ARRANCAR, no por
    request. Embeber los documentos es la operación cara; hacerla una sola vez
    mantiene baja la latencia de cada /ask. (En producción con Cloud Run, este
    índice saldría a un vector store gestionado para ser stateless.)
    """
    logger.info("Construyendo índice RAG al arrancar...")
    _state["store"] = build_index()
    logger.info("Índice RAG listo.")
    yield
    _state.clear()


app = FastAPI(
    title="Sumz RAG Assistant",
    description="Asistente de preguntas sobre documentos empresariales (RAG + Gemini).",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check: usado por Cloud Run / balanceadores para saber si el
    servicio está vivo. Imprescindible en producción."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """RAG completo: recupera contexto de los documentos y responde con citas.

    Manejo de errores de producción:
    - LLMUnavailableError (tras agotar reintentos) -> HTTP 503, mensaje claro.
    - Cualquier otro error inesperado -> HTTP 500 controlado, sin filtrar el
      stacktrace al cliente (los detalles quedan en el log del servidor).
    """
    start = time.perf_counter()
    # Logueamos la pregunta REDACTADA (sin PII): útil para debug/observabilidad
    # sin filtrar datos personales a Cloud Logging (OWASP LLM02).
    logger.info("ask recibida | pregunta=%r", redact_pii(request.question))
    try:
        result = answer_question(_state["store"], request.question)
    except LLMUnavailableError as exc:
        logger.error("LLM no disponible: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="El servicio de IA no está disponible temporalmente. Intenta de nuevo en unos segundos.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado procesando /ask")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error procesando la solicitud.",
        ) from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "ask ok | modelo=%s | fuentes=%d | tokens_in=%d | tokens_out=%d | "
        "costo_usd=%.6f | latencia=%.0fms",
        settings.gemini_model, len(result.sources),
        result.input_tokens, result.output_tokens, result.cost_usd, elapsed_ms,
    )
    return AskResponse(
        answer=result.answer,
        model=settings.gemini_model,
        sources=result.sources,
    )
