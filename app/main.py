"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="LeetCode Clone API",
    description="High-performance, asynchronous LeetCode backend with FastAPI, PostgreSQL, Redis, Celery, and AWS Cognito.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS) for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root access directly to interactive Swagger UI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
async def healthcheck():
    """Basic health check probe for load balancers and container orchestrators."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "mock_cognito": settings.MOCK_COGNITO,
    }
