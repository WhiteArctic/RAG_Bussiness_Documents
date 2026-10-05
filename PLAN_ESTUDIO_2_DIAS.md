# Plan de Estudio Intensivo — 2 Días
## Objetivo: Pasar entrevista técnica Mid-Senior · GenAI / LLM Implementation (Sumz)

> **Perfil de partida (autodiagnóstico):**
> - Python + FastAPI: **1-2** (reforzar bases)
> - LLMs / RAG: **3 básico** (core del rol → subir a "defiendo decisiones")
> - GCP / Despliegue: **1** (nunca → entender arquitectura y el *por qué*)
> - Tiempo: **4h/día = 8h totales**
> - Proveedor LLM del proyecto: **Google Gemini** (free tier, alineado con GCP)

## 🎯 Estrategia
Con 8 horas no se "domina" GCP ni RAG a nivel senior — y no hace falta. El cargo es de **integración y productización**, no de investigación. El objetivo real es:
> **Poder razonar y defender decisiones E2E en la entrevista, respaldado por UN mini-proyecto real que puedas contar: una API RAG en FastAPI que usa Gemini, con manejo de errores y pensada para producción en GCP.**
**Principio rector:** *Production first.* No basta con que "funcione en local".

## 📅 DÍA 1 — Integración LLM + RAG + API (el core del rol)
| Bloque | Tiempo | Tema | Entregable |
|---|---|---|---|
| **1** | 45 min | LLMs esenciales (teoría mínima defendible) | Notas + checks de entrevista |
| **2** | 60 min | FastAPI desde las bases → endpoint que llama a Gemini | `/ask` funcionando |
| **3** | 75 min | RAG de principio a fin | Ingesta → embeddings → retrieval → respuesta con citas |
| **4** | 60 min | Capa de producción (errores, 429, retries, validación) | API robusta + check Día 1 |
**Resultado Día 1:** Un servicio RAG local funcional y robusto.

## 📅 DÍA 2 — Producción en GCP + Operación + Simulacro
| Bloque | Tiempo | Tema | Entregable |
|---|---|---|---|
| **5** | 75 min | GCP de cero → arquitectura E2E (Cloud Run, Vertex AI, Secret Manager, IAM) | Dockerfile + diagrama + guía de despliegue |
| **6** | 45 min | LLMOps ligero (costos, latencia, observabilidad) | Logging estructurado + cálculo costo/request |
| **7** | 30 min | Seguridad GenAI (prompt injection, secretos, PII) | Checklist de seguridad aplicado |
| **8** | 90 min | **SIMULACRO DE ENTREVISTA** completo + feedback | Evaluación por dimensiones |
**Resultado Día 2:** Proyecto "listo para producción" (containerizado + guía GCP) y tú entrenado para defenderlo.

## 🗂️ Mapeo con tu curriculum original (7 fases → 2 días)
| Fase original | Dónde queda en el plan de 2 días |
|---|---|
| Fase 1 — Fundamentos | Comprimida en Bloques 2 y 4 (lo esencial de Python/API prod) |
| Fase 2 — LLMs | **Bloque 1** |
| Fase 3 — RAG | **Bloque 3** (núcleo) |
| Fase 4 — Aplicaciones | Bloques 2 y 4 |
| Fase 5 — Producción GCP | **Bloque 5** |
| Fase 6 — LLMOps | **Bloque 6** |
| Fase 7 — Proyecto final | **El mini-proyecto completo** (todos los bloques) |
| Seguridad / Responsible AI | **Bloque 7** |

## 📏 Método por bloque (de la skill)
Cada bloque sigue: **concepto → fundamento/trade-offs → ejemplo mínimo → versión producción → ejercicio tuyo → revisión → check de entrevista → conexión E2E.**

## 🧮 Evaluación (sin nota global)
Te evalúo por dimensiones: *Fundamentos · Implementación · Calidad de código · APIs · Diseño E2E · Evaluación de IA · Seguridad · GCP · Observabilidad · Pensamiento de producción · Justificación de trade-offs.*
Formato de feedback: **Correcto / Falta / Riesgo / Mejora / Siguiente reto.**

## 🔑 Reglas de seguridad del proyecto (desde el minuto 1)
- La API key **NUNCA** se escribe en el código ni en el chat.
- Se maneja con variables de entorno (`.env`) y `.env` va en `.gitignore`.
- Esto no es un detalle: es *exactamente* la buena práctica que evalúa el rol.

## 📦 Estructura objetivo del proyecto (se irá construyendo)
```
sumz-rag-assistant/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── app/
    ├── __init__.py        (vacío)
    ├── config.py
    ├── llm.py
    ├── main.py
    └── schemas.py
```
> `data/`, `tests/` y `app/rag.py` se añaden en el Bloque 3. El `Dockerfile` llega en el Día 2 (Bloque 5).
