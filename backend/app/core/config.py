from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VTAB Sentinel"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = "local-only-change-me"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./vtab.db"
    redis_url: str = "redis://redis:6379/0"
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_topic: str = "devices/+/telemetry"
    ai_service_url: str = "http://ai-service:8001"
    agent_provider: str = "local"
    agent_model: str = "evidence-first-2.0"
    llm_api_key: str = ""
    voice_provider: str = "browser"
    cors_origins: str = ""
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "vtabminio"
    s3_secret_key: str = "vtabminiosecret"
    s3_bucket: str = "vtab-sentinel"
    s3_region: str = "us-east-1"
    teams_webhook_url: str = ""
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    servicenow_base_url: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()



