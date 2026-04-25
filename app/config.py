from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://dld:dld@db:5432/datalineage_doctor"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # llm_api_key: str
    # llm_base_url: str = "https://api.cerebras.ai/v1"
    # llm_model: str = "llama3.1-8b"

    llm_api_key: str
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: int = 90
    llm_max_iterations: int = 10
    llm_client_max_retries: int = 0
    llm_rate_limit_retries: int = 1
    llm_rate_limit_backoff_seconds: int = 12

    om_base_url: str = "http://openmetadata_server:8585/api/v1"
    # Preferred: a non-expiring bot token (see knowledge/OM_jwt_token_generation.md)
    # If om_jwt_token is empty, the client will login using om_admin_* credentials.
    om_jwt_token: str = ""
    # Fallback credentials used for runtime token acquisition / auto-refresh on 401
    om_admin_email: str = "admin@open-metadata.org"
    om_admin_password: str = "YWRtaW4="  # base64("admin") — OM demo default
    om_max_lineage_depth: int = 3

    slack_enabled: bool = False
    slack_webhook_url: str = ""

    app_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
