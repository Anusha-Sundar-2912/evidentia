from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Evidentia"
    APP_VERSION: str = "0.1.0"

    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5433/evidentia"
    )

    REDIS_URL: str = "redis://localhost:6379/0"

    EMBEDDING_MODEL: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    GROQ_API_KEY: str

    LLM_MODEL: str = "openai/gpt-oss-120b"

    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()