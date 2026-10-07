"""Utilidades de seguridad: redacción de PII (datos personales).

Por qué (OWASP LLM02 - Sensitive Information Disclosure):
En un asistente de documentos empresariales, la pregunta del usuario o el
contexto pueden contener PII (emails, teléfonos, documentos de identidad). Si
logueamos ese texto en crudo, el PII termina en Cloud Logging -> fuga de datos.

Esta función ENMASCARA los patrones de PII más comunes antes de escribir logs.
Es una defensa mínima y pragmática (regex); en producción con PII sensible se
complementa con herramientas dedicadas como Google Cloud DLP (Data Loss
Prevention), que detectan muchos más tipos y con mayor precisión.
"""

import re

# Patrones de PII frecuentes. No pretende ser exhaustivo: cubre los casos más
# comunes para no filtrar lo evidente en los logs.
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Teléfonos: secuencias de 7+ dígitos, con espacios/guiones/paréntesis opcionales.
_PHONE = re.compile(r"\+?\d[\d\s\-()]{6,}\d")


def redact_pii(text: str) -> str:
    """Devuelve el texto con emails y teléfonos enmascarados.

    Ej.: "escribe a ana@acme.com o al 300 123 4567"
      -> "escribe a [EMAIL] o al [PHONE]"
    """
    if not text:
        return text
    redacted = _EMAIL.sub("[EMAIL]", text)
    redacted = _PHONE.sub("[PHONE]", redacted)
    return redacted
