from typing import List, Union

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def parse_cors_origins(v: Union[str, List[str]]) -> List[str]:
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "RiskLens Analytics"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Host Settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # Database Settings
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "risklens"
    POSTGRES_USER: str = "risklens_user"
    POSTGRES_PASSWORD: str = "risklens_password"
    DATABASE_URL: str = "postgresql+asyncpg://risklens_user:risklens_password@postgres:5432/risklens"

    # Testing Database Settings
    TEST_POSTGRES_DB: str = "risklens_test"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://risklens_user:risklens_password@postgres:5432/risklens_test"

    # JWT Settings
    JWT_SECRET_KEY: str = "replace-with-secure-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # User Policy Settings
    PASSWORD_MIN_LENGTH: int = 12

    # CORS Origins
    CORS_ORIGINS: Annotated[List[str], BeforeValidator(parse_cors_origins)] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Rate Limits
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_UPLOAD: str = "20/hour"
    RATE_LIMIT_AI: str = "20/hour"
    RATE_LIMIT_REPORT: str = "30/hour"

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/app/logs"
    LOG_ROTATE_WHEN: str = "H"
    LOG_ROTATE_INTERVAL: int = 1
    LOG_BACKUP_COUNT: int = 168

    # Storage Configuration
    MAX_UPLOAD_SIZE_MB: int = 500
    UPLOAD_DIR: str = "/app/storage/uploads"
    REPORT_DIR: str = "/app/storage/reports"
    ALLOWED_STRUCTURED_EXTENSIONS: str = ".csv,.xlsx,.json"
    ALLOWED_DOCUMENT_EXTENSIONS: str = ".pdf,.docx"

    # AI Providers Configuration
    AI_PROVIDER: str = "disabled"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL_NAME: str = ""
    AI_REQUEST_TIMEOUT_SECONDS: int = 60

    # Initial Seeding Credentials
    SEED_ADMIN_EMAIL: str = "admin@risklens.local"
    SEED_ADMIN_PASSWORD: str = "ChangeMeStrongPassword123!"
    SEED_ADMIN_FULL_NAME: str = "RiskLens Admin"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
