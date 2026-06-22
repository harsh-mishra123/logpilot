from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./logpilot.db"

    # Security — override SECRET_KEY in production via env var
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # WebSocket
    ws_max_size: int = 1048576
    ws_ping_interval: int = 20
    ws_ping_timeout: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()