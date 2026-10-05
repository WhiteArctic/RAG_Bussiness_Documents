# Sumz RAG Assistant

Asistente de preguntas sobre documentos empresariales (**RAG + Google Gemini**),
construido con **FastAPI**. Proyecto de preparación para entrevista Mid-Senior de
GenAI / LLM Implementation. Ver `PLAN_ESTUDIO_2_DIAS.md`.

> **Estado actual:** Bloques 1 y 2 terminados. El endpoint `/ask` llama a Gemini
> directamente (todavía **sin** retrieval). El RAG completo se implementa en el Bloque 3.

## Arquitectura (decisiones de diseño)

- **A mano con el SDK `google-genai`** (no LangChain / LlamaIndex): decisión
  pedagógica para entender el mecanismo del RAG de principio a fin.
- **Separación de responsabilidades:** `llm.py` solo habla con el LLM; `main.py`
  es la capa web; `schemas.py` es el contrato de la API; `config.py` centraliza
  la configuración.
- **Config por entorno (12-Factor):** secretos vía `.env`, validados con
  `pydantic-settings` (fail-fast si falta `GEMINI_API_KEY`).

## Estructura

```
sumz-rag-assistant/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── app/
    ├── __init__.py
    ├── config.py      # Settings (pydantic-settings), fail-fast
    ├── llm.py         # Integración Gemini (desacoplada de HTTP)
    ├── main.py        # FastAPI: /health y /ask
    └── schemas.py     # AskRequest / AskResponse (validación Pydantic)
```

## Modelos (Gemini free tier)

| Uso | Modelo |
|---|---|
| Generación | `gemini-2.5-flash` |
| Embeddings | `gemini-embedding-001` ⚠️ (NO `text-embedding-004`, descontinuado ene-2026) |

## Arranque local

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # editar .env y poner la API key real
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Docs interactivas (OpenAPI): http://127.0.0.1:8000/docs

## Endpoints

| Método | Ruta | Body | Respuesta |
|---|---|---|---|
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/ask` | `{"question": "..."}` | `{"answer": "...", "model": "gemini-2.5-flash"}` |

## Seguridad

- La API key **nunca** se hardcodea ni se versiona. `.env` está en `.gitignore`.
- `question` acotada a `max_length=2000` para mitigar *Unbounded Consumption*
  (OWASP LLM): costo, disponibilidad/DoS y superficie de prompt injection.

## Próximo (Bloque 3 — RAG completo)

`app/rag.py` + `data/`: ingesta → chunking → embeddings (`gemini-embedding-001`)
→ vector store en memoria (numpy) → retrieval top-k por similitud coseno →
contexto → generación con citas. El endpoint `/ask` pasará a usar RAG.
