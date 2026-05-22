from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./velai.db"
    jwt_secret_key: str = "change-me-in-development"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    llm_base_url: str = "http://localhost:4000/v1"
    llm_api_key: str = "local-dev-key"
    llm_model: str = "llama3.1"
    llm_enabled: bool = False
    llm_timeout_seconds: float = 5.0

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "recruitment_jobs"
    vector_size: int = 128

    live_search_enabled: bool = False
    live_search_timeout_seconds: float = 6.0
    strict_ai_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
