from fastapi import APIRouter
from app.api.v1.endpoints import auth, callbacks, problems, submissions, tags, users

api_router = APIRouter()

# Mount feature routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(problems.router, prefix="/problems", tags=["Problems"])
api_router.include_router(submissions.router, prefix="", tags=["Code Execution & Submissions"])
api_router.include_router(callbacks.router, prefix="/internal", tags=["Internal Webhooks"])
api_router.include_router(tags.router, prefix="/tags", tags=["Problem Tags"])
api_router.include_router(users.router, prefix="/users", tags=["User Profiles & Avatars"])
