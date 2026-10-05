"""FastAPI app: la capa web que expone la funcionalidad vía HTTP."""

from fastapi import FastAPI

from app.llm import generate_answer
from app.schemas import AskRequest, AskResponse
from app.config import settings

app = FastAPI(
    title="Sumz RAG Assistant",
    description="Asistente de preguntas sobre documentos empresariales (RAG + Gemini).",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check: usado por Cloud Run / balanceadores para saber si el
    servicio está vivo. Imprescindible en producción."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Recibe una pregunta y devuelve la respuesta del LLM.

    Por ahora llama a Gemini directamente (sin RAG todavía).
    En el Bloque 3 insertaremos el retrieval de documentos antes de generar.
    """
    answer = generate_answer(request.question)
    return AskResponse(answer=answer, model=settings.gemini_model)
