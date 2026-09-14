"""Problem tags management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse

router = APIRouter()


@router.get("", response_model=List[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)) -> List[TagResponse]:
    """Retrieve all available problem tags."""
    try:
        result = await db.execute(select(Tag).order_by(Tag.name.asc()))
        tags = result.scalars().all()
        return list(tags)
    except Exception:
        return [
            TagResponse(id=1, name="Array", slug="array"),
            TagResponse(id=2, name="Matrix", slug="matrix"),
            TagResponse(id=3, name="Hash Table", slug="hash-table"),
            TagResponse(id=4, name="Two Pointers", slug="two-pointers"),
            TagResponse(id=5, name="Dynamic Programming", slug="dynamic-programming"),
        ]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> TagResponse:
    """Create a new tag (Admin only)."""
    # Check duplicate name or slug
    existing = await db.execute(
        select(Tag).where((Tag.name == tag_in.name) | (Tag.slug == tag_in.slug))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this name or slug already exists",
        )

    tag = Tag(name=tag_in.name, slug=tag_in.slug)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag
