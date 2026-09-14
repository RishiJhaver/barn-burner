# LeetCode Clone — Backend

High-performance, asynchronous LeetCode clone backend built with **FastAPI**, **SQLAlchemy 2.0 (async)**, **PostgreSQL**, **Redis**, **Celery**, and **AWS Cognito**.

---

## Architecture Overview (Phase 1)

- **FastAPI Core**: Async API with dependency injection for database sessions.
- **SQLAlchemy 2.0 Async**: Declarative models using asyncpg.
- **Alembic Migrations**: Fully configured for async SQLAlchemy engine and revision management.
- **PostgreSQL Database Schema**:
  - `users`: UUID PK, Cognito sub index, role-based access.
  - `problems`: Serial PK, slug index, keyset pagination index on `(published, created_at DESC, id DESC)`.
  - `tags` & `problem_tags`: Many-to-many relationship.
  - `problem_templates`: Starter code per programming language.
  - `test_cases`: Input/output pairs with partial index for sample test cases.
  - `submissions`: UUID PK, code, verdict, runtime, memory, with partial index for submission history (`kind='submit'`).
  - `user_problem_status`: Attempted vs. Solved tracking per user/problem.

---

## Local Development Setup

### 1. Start Database & Cache
Ensure Docker is running and start PostgreSQL and Redis:
```bash
docker compose up -d
```

### 2. Python Environment Setup
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Run Database Migrations
Apply Alembic migrations to create tables and indexes:
```bash
alembic upgrade head
```

### 4. Run Model Tests
```bash
pytest tests/test_models.py
```
