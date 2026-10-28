"""S3 Object Storage Service with Dual-Mode (AWS Boto3 and Local Fallback)."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LOCAL_STORAGE_DIR = Path(".storage/s3")


class S3Service:
    """Manages S3 object storage for 100% of testcases and user avatars."""

    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.mock_s3 = settings.MOCK_S3

        if not self.mock_s3:
            # Production Boto3 S3 Client (supports IAM Instance Profile)
            self.client = boto3.client(
                "s3",
                region_name=self.region,
                config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
            )
        else:
            self.client = None
            # Ensure local fallback directory exists
            self.local_bucket_dir = LOCAL_STORAGE_DIR / self.bucket
            self.local_bucket_dir.mkdir(parents=True, exist_ok=True)

    def put_text(self, key: str, content: str, content_type: Optional[str] = None) -> str:
        """Upload text content to S3 or local storage."""
        if self.mock_s3:
            target_path = self.local_bucket_dir / key
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return key

        if not content_type:
            if key.endswith(".md"):
                content_type = "text/markdown; charset=utf-8"
            elif key.endswith(".json"):
                content_type = "application/json; charset=utf-8"
            else:
                content_type = "text/plain; charset=utf-8"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType=content_type,
            )
            return key
        except ClientError as exc:
            logger.error("Failed to upload to S3 key %s: %s", key, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage upload error: {str(exc)}",
            )

    def get_text(self, key: str) -> str:
        """Fetch text content from S3 or local storage."""
        if self.mock_s3:
            target_path = self.local_bucket_dir / key
            if not target_path.exists():
                return ""
            return target_path.read_text(encoding="utf-8")

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in ("NoSuchKey", "404", "NoSuchBucket"):
                return ""
            logger.warning("Failed to read from S3 key %s: %s", key, exc)
            return ""
        except Exception as exc:
            logger.warning("Unexpected error reading S3 key %s: %s", key, exc)
            return ""

    def upload_testcase(
        self, problem_id: int, tc_identifier: str, input_data: str, expected_output: str
    ) -> Tuple[str, str]:
        """Upload testcase input and expected output to S3, returning the keys."""
        input_key = f"testcases/{problem_id}/{tc_identifier}_input.txt"
        output_key = f"testcases/{problem_id}/{tc_identifier}_expected.txt"

        self.put_text(input_key, input_data)
        self.put_text(output_key, expected_output)

        return input_key, output_key

    def get_problem_testcase_bundle(
        self, problem_id: int, slug: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch consolidated testcase bundle JSON from S3 if available."""
        import json
        candidates = [
            f"problems/{slug}/testcases/bundle.json" if slug else None,
            f"problems/{slug}/bundle.json" if slug else None,
            f"testcases/{slug}/bundle.json" if slug else None,
            f"testcases/{problem_id}/bundle.json",
        ]

        for key in [c for c in candidates if c]:
            content = self.get_text(key)
            if content and content.strip():
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and "test_cases" in data:
                        return data
                except Exception as exc:
                    logger.warning("Failed to parse S3 bundle at %s: %s", key, exc)
        return None

    def put_problem_testcase_bundle(
        self, problem_id: int, bundle_data: Dict[str, Any], slug: Optional[str] = None
    ) -> str:
        """Store consolidated testcase bundle JSON into S3."""
        import json
        key = f"problems/{slug}/testcases/bundle.json" if slug else f"testcases/{problem_id}/bundle.json"
        self.put_text(key, json.dumps(bundle_data, indent=2))
        return key

    def get_problem_description(self, slug: str) -> Optional[str]:
        """Fetch problem description markdown file from S3."""
        candidates = [
            f"problems/{slug}/description.md",
            f"problems/{slug}/problem.md",
            f"problems/{slug}/README.md",
        ]
        for key in candidates:
            content = self.get_text(key)
            if content and content.strip():
                return content.strip()
        return None

    def put_problem_description(self, slug: str, markdown_content: str) -> str:
        """Store problem description markdown file into S3."""
        key = f"problems/{slug}/description.md"
        self.put_text(key, markdown_content, content_type="text/markdown; charset=utf-8")
        return key

    def list_problems(self) -> list[str]:
        """List slugs of problems stored under problems/ prefix in S3."""
        if self.mock_s3:
            problems_dir = self.local_bucket_dir / "problems"
            if not problems_dir.exists():
                return []
            return [d.name for d in problems_dir.iterdir() if d.is_dir()]

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            result = paginator.paginate(Bucket=self.bucket, Prefix="problems/", Delimiter="/")
            slugs = []
            for page in result:
                for prefix_info in page.get("CommonPrefixes", []):
                    prefix = prefix_info.get("Prefix", "")
                    slug = prefix.replace("problems/", "").strip("/")
                    if slug:
                        slugs.append(slug)
            return slugs
        except Exception as exc:
            logger.warning("Failed to list problems from S3: %s", exc)
            return []

    def generate_avatar_presigned_url(
        self, user_id: str, content_type: str = "image/webp", expires_in: int = 3600
    ) -> Dict[str, Any]:
        """Generate a presigned PUT URL for direct browser-to-S3 avatar upload."""
        key = f"avatars/{user_id}/avatar.webp"

        if self.mock_s3:
            # Mock presigned URL for local development
            mock_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}?mock_presigned=true&expires={expires_in}"
            return {
                "upload_url": mock_url,
                "key": key,
                "expires_in": expires_in,
                "headers": {"Content-Type": content_type},
            }

        try:
            presigned_url = self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return {
                "upload_url": presigned_url,
                "key": key,
                "expires_in": expires_in,
                "headers": {"Content-Type": content_type},
            }
        except ClientError as exc:
            logger.error("Failed to generate presigned URL for avatar: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL. Please try again later.",
            )

    # Asynchronous non-blocking wrappers using asyncio.to_thread
    async def put_text_async(self, key: str, content: str) -> str:
        import asyncio
        return await asyncio.to_thread(self.put_text, key, content)

    async def get_text_async(self, key: str) -> str:
        import asyncio
        return await asyncio.to_thread(self.get_text, key)

    async def upload_testcase_async(
        self, problem_id: int, tc_identifier: str, input_data: str, expected_output: str
    ) -> Tuple[str, str]:
        import asyncio
        return await asyncio.to_thread(
            self.upload_testcase, problem_id, tc_identifier, input_data, expected_output
        )

    async def generate_avatar_presigned_url_async(
        self, user_id: str, content_type: str = "image/webp", expires_in: int = 3600
    ) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(
            self.generate_avatar_presigned_url, user_id, content_type, expires_in
        )

    async def get_problem_testcase_bundle_async(
        self, problem_id: int, slug: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        import asyncio
        return await asyncio.to_thread(self.get_problem_testcase_bundle, problem_id, slug)

    async def put_problem_testcase_bundle_async(
        self, problem_id: int, bundle_data: Dict[str, Any], slug: Optional[str] = None
    ) -> str:
        import asyncio
        return await asyncio.to_thread(self.put_problem_testcase_bundle, problem_id, bundle_data, slug)

    async def get_problem_description_async(self, slug: str) -> Optional[str]:
        import asyncio
        return await asyncio.to_thread(self.get_problem_description, slug)

    async def put_problem_description_async(self, slug: str, markdown_content: str) -> str:
        import asyncio
        return await asyncio.to_thread(self.put_problem_description, slug, markdown_content)


# Singleton instance
s3_service = S3Service()

