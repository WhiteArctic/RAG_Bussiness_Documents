# Despliegue en GCP — Sumz RAG Assistant

Guía de referencia para llevar el servicio a producción en Google Cloud, y
chuleta de defensa para la entrevista. El principio rector es: **servicio
stateless** (el estado y los secretos viven fuera del proceso).

## Arquitectura E2E

```
                                 ┌─────────────────┐
   Cliente ──HTTPS──> Cloud Run ─┤  Secret Manager │ (inyecta GEMINI_API_KEY en runtime)
                         │        └─────────────────┘
                         │  (service account con mínimo privilegio · IAM)
                         ▼
                   ┌──────────────────────────┐
                   │  FastAPI (contenedor)     │
                   │   /ask  →  pipeline RAG    │
                   └──────────────────────────┘
                         │                 │
         embeber+generar ▼                 ▼ retrieval
                   ┌──────────┐      ┌───────────────────────┐
                   │ Vertex AI│      │ Vertex AI Vector Search│  (estado compartido
                   │ (Gemini) │      │                        │   → stateless)
                   └──────────┘      └───────────────────────┘

   Build:  docker build → Artifact Registry → Cloud Run deploy
   Obs.:   logs/métricas → Cloud Logging / Monitoring
```

## Componentes y por qué

| Servicio | Rol | Por qué |
|---|---|---|
| **Cloud Run** | Ejecuta el contenedor, serverless, autoescala | Sin gestionar servidores; paga por uso; encaja con servicio stateless |
| **Artifact Registry** | Almacena la imagen Docker | Cloud Run despliega desde una imagen registrada |
| **Secret Manager** | Guarda `GEMINI_API_KEY` cifrada | El secreto nunca va en la imagen; se inyecta en runtime |
| **Vertex AI** | Gemini + Vector Search gestionados | IAM nativo (sin key suelta) e índice fuera del proceso |
| **IAM** | Permisos de la service account | Mínimo privilegio: solo leer el secreto e invocar Vertex |
| **Cloud Logging / Monitoring** | Logs y métricas | Observabilidad, costos y alertas |

## Pasos de despliegue (referencia)

Requisitos: `gcloud` instalado y autenticado, un proyecto GCP con facturación.

```bash
# 0) Variables
export PROJECT_ID="tu-proyecto"
export REGION="us-central1"
export REPO="sumz-repo"
export SERVICE="sumz-rag-assistant"

# 1) Habilitar APIs necesarias
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com aiplatform.googleapis.com --project "$PROJECT_ID"

# 2) Crear el repositorio de imágenes
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker --location="$REGION" --project "$PROJECT_ID"

# 3) Guardar la API key como secreto (se lee desde stdin, NO queda en el historial)
printf '%s' "TU_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- --project "$PROJECT_ID"

# 4) Build y push de la imagen (Cloud Build construye el Dockerfile)
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$SERVICE:latest"
gcloud builds submit --tag "$IMAGE" --project "$PROJECT_ID"

# 5) Desplegar en Cloud Run, inyectando el secreto como variable de entorno
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest" \
  --project "$PROJECT_ID"
```

> El `--set-secrets` monta el secreto como la variable de entorno
> `GEMINI_API_KEY` en runtime. `pydantic-settings` la lee igual que en local
> desde `.env`: el código no cambia entre local y producción (12-Factor).

## Notas de producción

- **Costos:** Cloud Run cobra por request y por tiempo de CPU; escala a cero
  cuando no hay tráfico. Gemini/Vertex cobran por token (entrada+salida).
  Controlar costo = menos tokens (top_k ajustado, chunks concisos) + caché.
- **Cold starts:** la primera request tras escalar desde cero construye el
  índice (lifespan). Si el índice migra a Vector Search gestionado, el arranque
  es casi inmediato (solo conecta, no re-embebe).
- **Seguridad:** `--allow-unauthenticated` es para la demo. En producción se
  protege con IAM, API Gateway o un balanceador con autenticación.
- **Modelo:** confirmar el `GEMINI_MODEL` desplegado y su cuota antes de abrir
  tráfico real.
```
