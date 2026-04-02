from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    weaviate_url: str
    weaviate_api_key: str
    telegram_api_id: str | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    telegram_session_name: str = "telegram_session"

    model_config = {"env_file": ".env"}


settings = Settings()
