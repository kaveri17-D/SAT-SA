from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SAT-SA — Smart Assessment Tool for Security Analytics"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Air-Gap & Local-Only Guarantees
    STRICT_LOCAL_ONLY: bool = True
    IS_AIRGAPPED: bool = True

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "satsa_user"
    POSTGRES_PASSWORD: str = "satsa_secure_pass"
    POSTGRES_DB: str = "satsa_db"
    DATABASE_URL: str = "sqlite:///./satsa_dev.db"

    # Security
    SECRET_KEY: str = "sat-sa-supervisory-secret-key-change-in-production-airgap"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8888",
    ]

    # Ingestion & Analytics
    MAX_INGESTION_CHUNK_SIZE_MB: int = 50
    ENABLE_LOCAL_NLP: bool = True

    # Observability & Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "structured"

    # Backup & Recovery
    BACKUP_DIR: str = "data/backups"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @model_validator(mode="after")
    def enforce_production_guards(self):
        if self.ENVIRONMENT.lower() == "production":
            self.DEBUG = False
        return self

    @property
    def active_database_url(self) -> str:
        import os
        if os.environ.get("TESTING") == "1":
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            abs_db_path = os.path.join(base_dir, "satsa_test.db").replace("\\", "/")
            return f"sqlite:///{abs_db_path}"
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("sqlite:///./"):
                rel_path = self.DATABASE_URL.replace("sqlite:///./", "")
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                abs_db_path = os.path.join(base_dir, rel_path).replace("\\", "/")
                return f"sqlite:///{abs_db_path}"
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
