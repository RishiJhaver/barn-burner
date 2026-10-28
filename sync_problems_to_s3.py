"""Sync problems, markdown descriptions, templates, and testcases to/from AWS S3.

Usage:
    # 1. Sync all seed problems into S3 (creates description.md, metadata.json, templates.json, testcases/)
    python sync_problems_to_s3.py --upload

    # 2. Verify S3 bucket connection and list stored problems
    python sync_problems_to_s3.py --verify

    # 3. Import newly created problems from S3 into the PostgreSQL database
    python sync_problems_to_s3.py --import
"""

import os
import sys
import json
import argparse
import asyncio
from typing import Dict, Any, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from seed_problems import SEED_DATA

settings = get_settings()


def get_s3_client(region: str):
    """Instantiate a Boto3 S3 client using IAM Instance Profile or AWS credentials."""
    return boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def verify_s3(bucket: str, region: str):
    """Verify S3 connectivity, permissions, and list existing problems."""
    print(f"\n🔍 Testing S3 connectivity for bucket '{bucket}' in region '{region}'...")
    s3 = get_s3_client(region)
    try:
        # Check bucket existence
        s3.head_bucket(Bucket=bucket)
        print(f"✅ Successfully connected to S3 bucket: {bucket}")
    except ClientError as e:
        print(f"❌ Error accessing bucket '{bucket}': {e}")
        return False

    # Test write/read permissions
    test_key = "healthcheck/_test_connectivity.txt"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=test_key,
            Body=b"S3 Connection OK",
            ContentType="text/plain",
        )
        resp = s3.get_object(Bucket=bucket, Key=test_key)
        body = resp["Body"].read().decode("utf-8")
        s3.delete_object(Bucket=bucket, Key=test_key)
        print(f"✅ Read/Write/Delete verification succeeded (Echo: '{body}')")
    except Exception as e:
        print(f"❌ Read/Write test failed: {e}")
        return False

    # List problems
    print("\n📂 Scanning for existing problems in S3 (prefix 'problems/'):")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix="problems/", Delimiter="/")
    slugs = []
    for page in pages:
        for prefix_info in page.get("CommonPrefixes", []):
            slug = prefix_info.get("Prefix", "").replace("problems/", "").strip("/")
            if slug:
                slugs.append(slug)

    if slugs:
        print(f"Found {len(slugs)} problems in S3:")
        for s in slugs:
            print(f"  • problems/{s}/")
    else:
        print("  (No problems uploaded yet. Run with --upload to push problems!)")

    return True


def upload_problem_to_s3(s3, bucket: str, problem_data: Dict[str, Any]):
    """Upload a single problem's markdown, metadata, templates, and testcase bundle."""
    slug = problem_data["slug"]
    title = problem_data["title"]
    diff = problem_data["difficulty"].value if hasattr(problem_data["difficulty"], "value") else str(problem_data["difficulty"])
    tags = problem_data.get("tags", [])
    description_md = problem_data["description"].strip()
    templates = problem_data.get("templates", [])
    test_cases = problem_data.get("test_cases", [])

    print(f"\n📤 Uploading problem: {title} ({slug}) to s3://{bucket}/problems/{slug}/ ...")

    # 1. Upload description.md
    desc_key = f"problems/{slug}/description.md"
    s3.put_object(
        Bucket=bucket,
        Key=desc_key,
        Body=description_md.encode("utf-8"),
        ContentType="text/markdown; charset=utf-8",
    )
    print(f"   ✓ {desc_key}")

    # 2. Upload metadata.json
    meta_key = f"problems/{slug}/metadata.json"
    meta_data = {
        "slug": slug,
        "title": title,
        "difficulty": diff,
        "tags": tags,
        "published": problem_data.get("published", True),
    }
    s3.put_object(
        Bucket=bucket,
        Key=meta_key,
        Body=json.dumps(meta_data, indent=2).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )
    print(f"   ✓ {meta_key}")

    # 3. Upload templates.json
    tmpl_key = f"problems/{slug}/templates.json"
    s3.put_object(
        Bucket=bucket,
        Key=tmpl_key,
        Body=json.dumps(templates, indent=2).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )
    print(f"   ✓ {tmpl_key}")

    # 4. Upload testcases/bundle.json
    bundle_key = f"problems/{slug}/testcases/bundle.json"
    bundle_data = {
        "slug": slug,
        "title": title,
        "test_cases": [
            {
                "id": idx + 1,
                "input": tc.get("input", ""),
                "expected_output": tc.get("expected_output", ""),
                "is_sample": tc.get("is_sample", False),
            }
            for idx, tc in enumerate(test_cases)
        ],
    }
    s3.put_object(
        Bucket=bucket,
        Key=bundle_key,
        Body=json.dumps(bundle_data, indent=2).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )
    print(f"   ✓ {bundle_key} ({len(test_cases)} test cases)")

    # 5. Upload individual test case files for convenience & manual browsing
    for idx, tc in enumerate(test_cases):
        in_key = f"problems/{slug}/testcases/{idx + 1}_input.txt"
        out_key = f"problems/{slug}/testcases/{idx + 1}_expected.txt"
        s3.put_object(
            Bucket=bucket,
            Key=in_key,
            Body=tc.get("input", "").encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        s3.put_object(
            Bucket=bucket,
            Key=out_key,
            Body=tc.get("expected_output", "").encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

    print(f"   ✓ Uploaded {len(test_cases)} individual testcase files to problems/{slug}/testcases/")


def upload_all_problems(bucket: str, region: str):
    """Upload all problems from SEED_DATA to S3."""
    print(f"🚀 Starting upload of {len(SEED_DATA)} problems to S3 bucket: {bucket}")
    s3 = get_s3_client(region)
    for problem in SEED_DATA:
        upload_problem_to_s3(s3, bucket, problem)
    print(f"\n🎉 All {len(SEED_DATA)} problems successfully synced to S3!")


async def import_problems_from_s3(bucket: str, region: str):
    """Scan S3 problems/ directory and insert or update them in the PostgreSQL database."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.problem import Problem
    from app.models.tag import Tag
    from app.models.template import ProblemTemplate
    from app.models.test_case import TestCase
    from app.models.enums import ProblemDifficulty

    print(f"\n📥 Scanning S3 bucket '{bucket}' for problem folders to import into PostgreSQL...")
    s3 = get_s3_client(region)
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix="problems/", Delimiter="/")
    slugs = []
    for page in pages:
        for prefix_info in page.get("CommonPrefixes", []):
            slug = prefix_info.get("Prefix", "").replace("problems/", "").strip("/")
            if slug:
                slugs.append(slug)

    if not slugs:
        print("No problems found in S3 under problems/.")
        return

    print(f"Found {len(slugs)} problems in S3: {slugs}")

    async with AsyncSessionLocal() as db:
        for slug in slugs:
            print(f"\nProcessing problem from S3: {slug}...")
            # 1. Fetch description.md
            try:
                desc_obj = s3.get_object(Bucket=bucket, Key=f"problems/{slug}/description.md")
                description = desc_obj["Body"].read().decode("utf-8")
            except Exception as e:
                print(f"  ⚠️ Warning: No description.md found for {slug} ({e})")
                description = ""

            # 2. Fetch metadata.json
            try:
                meta_obj = s3.get_object(Bucket=bucket, Key=f"problems/{slug}/metadata.json")
                meta = json.loads(meta_obj["Body"].read().decode("utf-8"))
            except Exception:
                meta = {
                    "title": slug.replace("-", " ").title(),
                    "difficulty": "MEDIUM",
                    "tags": [],
                    "published": True,
                }

            # 3. Fetch templates.json
            try:
                tmpl_obj = s3.get_object(Bucket=bucket, Key=f"problems/{slug}/templates.json")
                templates_data = json.loads(tmpl_obj["Body"].read().decode("utf-8"))
            except Exception:
                templates_data = []

            # 4. Fetch testcases/bundle.json
            try:
                bundle_obj = s3.get_object(Bucket=bucket, Key=f"problems/{slug}/testcases/bundle.json")
                bundle = json.loads(bundle_obj["Body"].read().decode("utf-8"))
                test_cases_data = bundle.get("test_cases", [])
            except Exception:
                test_cases_data = []

            # Check if problem already exists in DB
            stmt = select(Problem).where(Problem.slug == slug)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()

            diff_str = meta.get("difficulty", "MEDIUM").upper()
            difficulty = getattr(ProblemDifficulty, diff_str, ProblemDifficulty.MEDIUM)

            if existing:
                print(f"  Updating existing database record for {slug}...")
                existing.title = meta.get("title", existing.title)
                existing.description = description if description else existing.description
                existing.difficulty = difficulty
                existing.published = meta.get("published", True)
                problem_id = existing.id
            else:
                print(f"  Creating new database record for {slug}...")
                new_problem = Problem(
                    slug=slug,
                    title=meta.get("title", slug.replace("-", " ").title()),
                    description=description,
                    difficulty=difficulty,
                    published=meta.get("published", True),
                )
                db.add(new_problem)
                await db.flush()
                problem_id = new_problem.id

            # Add / Update templates
            for tmpl in templates_data:
                lang = tmpl.get("language")
                code = tmpl.get("starter_code", "")
                tmpl_stmt = select(ProblemTemplate).where(
                    ProblemTemplate.problem_id == problem_id,
                    ProblemTemplate.language == lang,
                )
                tmpl_res = await db.execute(tmpl_stmt)
                existing_tmpl = tmpl_res.scalar_one_or_none()
                if existing_tmpl:
                    existing_tmpl.starter_code = code
                else:
                    db.add(ProblemTemplate(problem_id=problem_id, language=lang, starter_code=code))

            # Add / Update sample testcases
            for tc in test_cases_data:
                tc_inp = tc.get("input", "")
                tc_out = tc.get("expected_output", "")
                tc_sample = tc.get("is_sample", False)
                tc_stmt = select(TestCase).where(
                    TestCase.problem_id == problem_id,
                    TestCase.input == tc_inp,
                )
                tc_res = await db.execute(tc_stmt)
                if not tc_res.scalar_one_or_none():
                    db.add(TestCase(
                        problem_id=problem_id,
                        input=tc_inp,
                        expected_output=tc_out,
                        is_sample=tc_sample,
                    ))

            await db.commit()
            print(f"  ✅ Successfully synced {slug} to PostgreSQL database!")

    print("\n🎉 All problems from S3 imported/updated in PostgreSQL successfully!")


def main():
    parser = argparse.ArgumentParser(description="Sync problem markdown & testcases to/from S3")
    parser.add_argument("--upload", action="store_true", help="Upload all seed problems to S3")
    parser.add_argument("--verify", action="store_true", help="Verify S3 connectivity and permissions")
    parser.add_argument("--import", dest="import_from_s3", action="store_true", help="Import problems from S3 into PostgreSQL")
    parser.add_argument("--bucket", default=os.getenv("S3_BUCKET_NAME", settings.S3_BUCKET_NAME or "leetcode-rishi-problems"), help="S3 bucket name")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "ap-south-1"), help="AWS region")

    args = parser.parse_args()

    # Default action if no flags provided: verify and upload
    if not args.upload and not args.verify and not args.import_from_s3:
        args.verify = True
        args.upload = True

    if args.verify:
        ok = verify_s3(args.bucket, args.region)
        if not ok and not args.upload and not args.import_from_s3:
            sys.exit(1)

    if args.upload:
        upload_all_problems(args.bucket, args.region)

    if args.import_from_s3:
        asyncio.run(import_problems_from_s3(args.bucket, args.region))


if __name__ == "__main__":
    main()
