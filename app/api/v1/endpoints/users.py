"""User profile and avatar management endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_user
from app.models.user import User
from app.services.s3_service import s3_service

router = APIRouter()


@router.post("/me/avatar/presigned-url", response_model=Dict[str, Any])
async def get_avatar_upload_url(
    content_type: str = Query("image/webp", description="MIME type of the avatar image"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate an S3 presigned PUT URL allowing the authenticated user
    to directly upload their avatar image to AWS S3.
    """
    return s3_service.generate_avatar_presigned_url(
        user_id=str(current_user.id),
        content_type=content_type,
    )
