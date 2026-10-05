"""Configuración centralizada, cargada desde variables de entorno.

Por qué este patrón (y por qué importa en la entrevista):
- Los secretos (API keys) NUNCA van hardcodeados en el código.
- 12-Factor App: la configuración vive en el entorno, no en el código.
- pydantic-settings valida que la config exista y tenga el tipo correcto
  al arrancar la app (fail-fast): si falta GEMINI_API_KEY, la app no arranca
  en silencio, falla de inmediato con un error claro.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Lee automáticamente desde variables de entorno y desde un archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str  # obligatorio: si falta, la app no arranca (fail-fast)
    gemini_model: str = "gemini-2.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"


# Instancia única reutilizable en toda la app.
settings = Settings()  # type: ignore[call-arg]
