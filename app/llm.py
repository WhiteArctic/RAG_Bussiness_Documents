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
