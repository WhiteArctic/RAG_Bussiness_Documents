"""Integración con el LLM (Google Gemini).

Separación de responsabilidades: este módulo solo sabe de "hablar con el LLM".
No sabe nada de HTTP, FastAPI ni endpoints. Eso lo hace testeable y permite
cambiar de proveedor sin tocar la capa web.
"""

from google import genai
from google.genai import types

from app.config import settings

# Cliente único, creado una vez. Lee la API key que le pasamos explícitamente.
_client = genai.Client(api_key=settings.gemini_api_key)


def generate_answer(prompt: str, temperature: float = 0.1) -> str:
    """Envía un prompt a Gemini y devuelve el texto de la respuesta.

    temperature baja (0.1) por defecto: queremos respuestas factuales y
    reproducibles para un asistente de documentos, no creatividad.
    """
    response = _client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return response.text or ""


# ---------------------------------------------------------------------------
# EMBEDDINGS
# ---------------------------------------------------------------------------
# OJO: este es un modelo DISTINTO al generativo. gemini-embedding-001 convierte
# texto en vectores (para buscar); gemini-2.5-flash escribe respuestas (para
# responder). No confundirlos: es un error clásico en entrevistas de RAG.
#
# task_type: Gemini optimiza el embedding según su propósito.
#   - RETRIEVAL_DOCUMENT: para los textos que vamos a INDEXAR (los chunks).
#   - RETRIEVAL_QUERY:     para la PREGUNTA del usuario al buscar.
# Usar el task_type correcto mejora la calidad del match asimétrico
# (una pregunta corta contra un documento largo).


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Convierte una lista de textos en una lista de vectores (batch).

    Se usa en la INGESTA, una sola vez al indexar: embeber documentos es caro,
    no se repite en cada request. Por eso va en batch.
    """
    if not texts:
        return []
    response = _client.models.embed_content(
        model=settings.gemini_embed_model,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return [list(e.values) for e in response.embeddings]


def embed_query(text: str) -> list[float]:
    """Convierte UNA pregunta en un vector. Se ejecuta en caliente, por request.

    Usa task_type=RETRIEVAL_QUERY: el lado 'pregunta' del match asimétrico.
    """
    response = _client.models.embed_content(
        model=settings.gemini_embed_model,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return list(response.embeddings[0].values)
