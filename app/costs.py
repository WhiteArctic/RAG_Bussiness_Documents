"""Cálculo de costo por request (LLMOps).

El costo de un LLM se mide en TOKENS: se paga por tokens de entrada (prompt) y
de salida (respuesta), a precios distintos. Centralizamos aquí los precios y la
fórmula para poder:
  - loguear el costo estimado de cada request,
  - ajustar precios en un solo sitio si cambian,
  - razonar sobre palancas de ahorro (menos contexto, modelo más barato).

IMPORTANTE: los precios cambian y dependen del modelo/region. Son valores de
referencia, configurables. En producción se validan contra la tarifa vigente.
"""

# Precios de referencia por 1 MILLÓN de tokens, en USD (ajustar al vigente).
# Estructura: modelo -> (precio_entrada, precio_salida) por 1M tokens.
_PRICING_PER_MILLION: dict[str, tuple[float, float]] = {
    # Familia flash: barata, pensada para alto volumen / baja latencia.
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-1.5-flash": (0.075, 0.30),
    # Fallback genérico si el modelo no está en la tabla (conservador).
    "_default": (0.10, 0.40),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estima el costo en USD de una generación dada su cuenta de tokens.

    costo = (in_tokens/1e6)*precio_in + (out_tokens/1e6)*precio_out
    """
    price_in, price_out = _PRICING_PER_MILLION.get(model, _PRICING_PER_MILLION["_default"])
    cost = (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out
    return round(cost, 8)
