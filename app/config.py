from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://dld:dld@db:5432/datalineage_doctor"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    llm_api_key: str
    llm_base_url: str = "https://api.cerebras.ai/v1"
    llm_model: str = "llama3.1-8b"
    llm_timeout_seconds: int = 90
    llm_max_iterations: int = 4
    llm_client_max_retries: int = 0
    llm_rate_limit_retries: int = 1
    llm_rate_limit_backoff_seconds: int = 12

    om_base_url: str = "http://openmetadata_server:8585/api/v1"
    om_jwt_token: str
    om_max_lineage_depth: int = 3

    slack_enabled: bool = False
    slack_webhook_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
