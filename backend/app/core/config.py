from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    api_key: str = "ratescope-demo-key"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    database_url: str = "postgresql+psycopg2://ratescope:ratescope@localhost:5432/ratescope"
    redis_url: str = "redis://localhost:6379/0"

    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_topic_rates: str = "supplier.rates"
    kafka_topic_dlq: str = "supplier.rates.dlq"
    kafka_topic_retry: str = "supplier.rates.retry"
    kafka_consumer_group: str = "ratescope-ingestor"

    parity_threshold_pct: float = 8.0
    parity_high_pct: float = 20.0
    parity_medium_pct: float = 12.0
    anomaly_zscore: float = 2.5
    anomaly_window: int = 24
    alert_cooldown_minutes: int = 30

    simulator_speed: float = 1.0
    simulator_interval_seconds: float = 2.0
    demo_mode: bool = True

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 12.0

    run_consumer: bool = False
    rate_limit_per_minute: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
