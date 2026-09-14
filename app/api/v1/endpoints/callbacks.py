"""Judge0 asynchronous webhook callback receiver."""

import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.enums import SubmissionStatus
from app.models.submission import Submission
from app.services.judge0_service import JUDGE0_STATUS_MAP

logger = logging.getLogger(__name__)
router = APIRouter()


@router.put("/judge0-callback", status_code=status.HTTP_200_OK)
@router.post("/judge0-callback", status_code=status.HTTP_200_OK)
async def judge0_callback(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Webhook endpoint invoked by Judge0 when asynchronous submissions complete.
    Updates the database with execution status, runtime, and memory.
    """
    token = payload.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'token' in callback payload",
        )

    async with AsyncSessionLocal() as db:
        stmt = select(Submission).where(Submission.judge0_token == token)
        res = await db.execute(stmt)
        submission = res.scalar_one_or_none()

        if not submission:
            logger.warning("No submission found for Judge0 token %s", token)
            return {"status": "ignored"}

        # Map status
        status_id = payload.get("status", {}).get("id", 13)
        normalized_status = JUDGE0_STATUS_MAP.get(status_id, SubmissionStatus.INTERNAL_ERROR)

        time_val = payload.get("time")
        runtime_ms = int(float(time_val) * 1000) if time_val else 0
        memory_kb = int(payload.get("memory") or 0)
        stderr = payload.get("stderr") or payload.get("compile_output")

        submission.status = normalized_status
        submission.runtime_ms = runtime_ms
        submission.memory_kb = memory_kb
        submission.error_message = stderr

        await db.commit()

    return {"status": "processed"}
