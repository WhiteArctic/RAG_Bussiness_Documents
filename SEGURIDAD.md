# Seguridad GenAI — Sumz RAG Assistant

Checklist de seguridad aplicado al proyecto, mapeado al **OWASP Top 10 for LLM
Applications**. Sirve como referencia de las defensas implementadas y como
chuleta para la entrevista.

## Resumen por riesgo

| OWASP | Riesgo | Estado | Defensa en este proyecto |
|---|---|---|---|
| **LLM01** | Prompt Injection | ✅ Mitigado | Reglas en `system_instruction` (separadas del input del usuario como dato) + regla defensiva explícita que ignora intentos de override |
| **LLM02** | Divulgación de info sensible | ✅ Mitigado | Secretos vía Secret Manager/`.env` (nunca en código ni imagen); PII redactada antes de loguear (`security.redact_pii`) |
| **LLM05** | Manejo inseguro de salidas | ⚠️ Parcial | Errores controlados (503/500 sin stacktrace); pendiente: validar/sanear la salida si se renderiza en HTML |
| **LLM06** | Agencia excesiva | ✅ N/A | El RAG solo lee documentos y responde; no ejecuta acciones ni tiene herramientas con efectos secundarios |
| **LLM08** | Debilidades de embeddings/vector store | ⚠️ Parcial | Control de la fuente de `data/` (ingesta curada); pendiente: validación de documentos no confiables |
| **LLM10** | Consumo no acotado (costo/DoS) | ✅ Mitigado | `max_length=2000` en la pregunta; reintentos con tope; `temperature` baja; costo medido por request |

## Detalle de las defensas

### 1. Prompt Injection (LLM01)
- Las instrucciones del sistema viajan en `system_instruction`, NO concatenadas
  con el texto del usuario. El input del usuario se trata como **dato**, no como
  instrucción.
- Regla defensiva #5 en el system prompt: ignora cualquier intento de cambiar,
  anular o revelar las reglas.
- No existe defensa perfecta: es **defensa en profundidad**. Mejora futura:
  guardrail de validación de salida.

### 2. Manejo de secretos (LLM02)
- `GEMINI_API_KEY` nunca en el código. En local: `.env` (en `.gitignore`).
- En producción: **Secret Manager**, inyectado como variable de entorno en
  runtime por Cloud Run. `.dockerignore` evita que `.env` entre en la imagen.
- La key nunca se escribe en logs ni se devuelve al cliente.

### 3. PII (LLM02)
- La pregunta del usuario se **redacta** (emails/teléfonos → `[EMAIL]`/`[PHONE]`)
  antes de escribir cualquier log.
- Mejora para producción: **Google Cloud DLP** para detección robusta de PII
  (cédulas, tarjetas, nombres) en documentos y respuestas.

### 4. Consumo no acotado (LLM10)
- `max_length=2000` en la pregunta → limita tokens de entrada (costo + superficie
  de injection).
- Reintentos con **tope** (no infinitos) y backoff → no amplifica saturación.
- Costo medido por request → base para alertas de gasto anómalo.

## Pendientes / mejoras futuras
- Rate limiting por cliente (API Gateway / Cloud Armor) ante abuso.
- Guardrail de validación de la salida (que no filtre el system prompt ni PII).
- Autenticación (quitar `--allow-unauthenticated` en producción real).
- Cloud DLP para PII en documentos y respuestas.
