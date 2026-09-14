from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/leetcode_clone"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgrespassword@localhost:5432/leetcode_clone"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # AWS Services (Cognito & S3 via Boto3)
    AWS_REGION: str = "us-east-1"
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_APP_CLIENT_ID: str = ""
    COGNITO_ISSUER: str = ""
    S3_BUCKET_NAME: str = "leetcode-clone-storage"
    MOCK_S3: bool = True

    # Cache TTLs (seconds)
    CACHE_PROBLEMS_LIST_TTL: int = 60
    CACHE_PROBLEM_DETAIL_TTL: int = 300

    # Local Auth & Demo Mode
    MOCK_COGNITO: bool = True
    DEMO_JWT_SECRET: str = "demo-local-jwt-secret-key-32-chars-min"

    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Judge0 Configuration
    MOCK_JUDGE0: bool = True
    JUDGE0_URL: str = "http://localhost:2358"
    JUDGE0_CALLBACK_URL: str = "http://localhost:8000/internal/judge0-callback"
    JUDGE0_CPU_TIME_LIMIT: float = 2.0
    JUDGE0_MEMORY_LIMIT: int = 128000
    MAX_CODE_LENGTH_BYTES: int = 65536

    # Rate Limiting (Anti-Spam Short Window; No Daily Limit)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_RUN_PER_MINUTE: int = 15
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def jwks_url(self) -> str:
        if self.COGNITO_ISSUER:
            return f"{self.COGNITO_ISSUER.rstrip('/')}/.well-known/jwks.json"
        return f"https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
