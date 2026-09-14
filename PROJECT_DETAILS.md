# CodeGrid (LeetCode Clone) — Complete System Architecture & Project Details

> **Last Updated**: September 2026  
> **Repository**: [RishiJhaver/barn-burner](https://github.com/RishiJhaver/barn-burner.git)  
> **Status**: Production-Ready / Phase 7 Cloud Deployment Ready  

---

## 1. Executive Summary

CodeGrid is a high-performance, asynchronous online judge and algorithmic contest platform built to mirror LeetCode's core capabilities while delivering a cutting-edge, minimalist developer experience.

### Core Stack
- **Backend**: Python 3.13, FastAPI (ASGI async), SQLAlchemy 2.0 (asyncpg), Pydantic v2
- **Database**: PostgreSQL 16 with async connection pooling and JIT auto-provisioning
- **Caching & Tasks**: Redis 7, Celery async task queue
- **Sandbox Execution Engine**: Judge0 API with single-call multi-testcase batching
- **Storage & Auth**: AWS S3 (testcase bundles & problem assets), AWS Cognito (User Pools with RS256 JWKS)
- **Frontend**: React 18, TypeScript, TailwindCSS v3, Vite, Monaco Editor

---

## 2. Authentication & Authorization Architecture

The system features a **Dual-Mode Authentication Gateway** supporting both zero-dependency local development and production AWS Cognito User Pools.

```
                  ┌──────────────────────────────────────────────┐
                  │            CodeGrid React Frontend           │
                  │  (Sign In / Register / Email OTP / Presets)  │
                  └───────────────────────┬──────────────────────┘
                                          │ POST /api/v1/auth/*
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │              FastAPI Backend Gateway         │
                  └───────┬──────────────────────────────┬───────┘
                          │                              │
          MOCK_COGNITO=False (Production)        MOCK_COGNITO=True (Dev)
                          ▼                              ▼
            ┌───────────────────────────┐  ┌───────────────────────────┐
            │   AWS Cognito User Pool   │  │   Local Mock Simulator    │
            │  • InitiateAuth (USER_PWD)│  │  • Mock In-Memory Store   │
            │  • SignUp & ConfirmSignUp │  │  • Instant OTP (123456)   │
            │  • Forgot/ConfirmPassword │  │  • 1-Click Dev Presets    │
            │  • RS256 JWKS Key Set     │  │  • Cryptographic HS256    │
            └─────────────┬─────────────┘  └─────────────┬─────────────┘
                          │                              │
                          └──────────────┬───────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          PostgreSQL Database Sync            │
                  │  • users table (UUID PK, cognito_sub index)  │
                  │  • Role-Based Access Control (user / admin)  │
                  └──────────────────────────────────────────────┘
```

### Key Components

1. **`CognitoService` (`app/services/cognito_service.py`)**:
   - `sign_up(username, email, password, role)`: Initiates account registration.
   - `confirm_sign_up(username, confirmation_code)`: Validates the 6-digit email confirmation code.
   - `resend_confirmation_code(username)`: Resends verification codes.
   - `initiate_auth(username_or_email, password)`: Authenticates via `USER_PASSWORD_AUTH` flow and returns JWT tokens (`AccessToken`, `IdToken`) and claims.
   - `forgot_password(username_or_email)` & `confirm_forgot_password(username, code, new_password)`: Self-service password recovery flow.
   - **Local Mock Simulator**: If `MOCK_COGNITO=True`, provides instant demo OTP (`123456`) and local token creation without an AWS account.

2. **Database JIT Sync (`app/api/v1/endpoints/auth.py` & `app/api/deps.py`)**:
   - Upon successful Cognito authentication, the user is idempotently created or updated in PostgreSQL.
   - In offline DB environments, fallback synthesizes an ephemeral user from verified JWT claims, ensuring zero interruption.

3. **Role-Based Access Control (RBAC)**:
   - `UserRole.USER` (Standard Coder): Access to solve problems, submit code, view personal stats.
   - `UserRole.ADMIN` (Problem Setter): Access to publish problems, manage testcases, and pass the `/admin-check` guard.

4. **Frontend Auth Suite (`frontend/src/components/LoginModal.tsx`)**:
   - **Sign In Tab**: Handle/Email + Password, Show/Hide password toggle, recovery link.
   - **Register Tab**: Coder Handle, Email, Password, Confirm Password, Role selector (`Coder` vs `Setter`).
   - **Email OTP Verification**: 6-digit monospace code input, resend button with timer.
   - **Password Reset**: Email prompt -> OTP verification + new password.
   - **1-Click Developer Presets**: Quick switch between `Coder Alex` and `Admin Elena`.
   - **Gateway Status Badge**: Real-time indicator showing `AWS Cognito Live` (green pulse) vs `Cognito Auth Gateway` (sandbox).

---

## 3. LeetCode-Style Test Harness Service (`HarnessService`)

Instead of spinning up N separate Judge0 sandbox containers for N testcases (which is slow and expensive), CodeGrid stitches user code into a hidden language-specific driver and executes all testcases in a **single sandbox run**.

### Protocol Delimiters
- **`TESTCASE_DELIMITER`**: `===TESTCASE_BOUNDARY===` (separates batched inputs sent to stdin)
- **`OUTPUT_DELIMITER`**: `===OUTPUT_BOUNDARY===` (separates testcase outputs emitted to stdout)

### Supported Languages
1. **Python**: Solution class dynamic reflection dispatcher, `sys.stdin` stream splitter, `ast.literal_eval` fallback, tuple array serialization.
2. **C++**: Regex signature extraction, access-specifier stripping, built-in deserializers (`parseInt`, `parseLongLong`, `parseDouble`, `parseFloat`, `parseBool`, `parseChar`, `parseString`, `parseVectorInt`, `parseVectorLong`, `parseVectorString`, `parseMatrixInt`), overloaded template `printResult`.
3. **Java**: Main class wrapper, bracket-aware generic parameter splitter, deserializers (`parseIntArray`, `parseLongArray`, `parse2DIntArray`, `parseStringArray`, `parseChar`, `parseListInt`, `parseListString`, `parseString`).
4. **JavaScript**: Node.js `fs.readFileSync(0, 'utf-8')` runner, safe function resolution without template-literal injection risks.

### The 8 Harness Audit Fixes
| # | Bug | Root Cause | Implemented Solution |
|---|-----|------------|----------------------|
| 1 | **Stdin Desync on Unmatched Signatures** | If signature regex failed, stdin wasn't drained, causing next testcase to read stale lines. | Added explicit stdin drain loops in C++ and Java consuming input up to `TESTCASE_DELIMITER` or EOF. |
| 2 | **Java Comma-Split Breaking Generics** | Naive `split(",")` broke generic brackets like `Map<String, Integer>`. | Reused bracket-depth-aware `_split_cpp_params` in Java harness generator. |
| 3 | **Fallback Parser Type Mismatches** | Less common types (`long`, `float`, `char`, `String[]`, `List<T>`) declared as `String`. | Implemented dedicated parsers for primitives/lists and aligned fallback variable declarations with `String`. |
| 4 | **Zero-Argument Void Method Crash** | For `void` methods with 0 args, `arg_names[0]` threw Python `IndexError`. | Added empty `arg_names` guard: calls `solver.method()` directly and prints `"null"`. |
| 5 | **Python Tuple JSON Serialization** | Tuples fell through `isinstance(res, (list, dict, bool))` to `str()`, printing `(1, 2)`. | Added `tuple` to the serialization tuple so output formats as JSON array `[1, 2]`. |
| 6 | **JavaScript Template Literal Injection** | Raw `user_code` was embedded inside a JS template literal `` `${user_code}` ``. | Pre-extracted candidate function names via Python regex and passed as safe string literals. |
| 7 | **Missing Float Tolerance** | Floats with minute differences (`3.1415926` vs `3.14159`) failed exact string/JSON checks. | Added `math.isclose` with `1e-5` tolerance for scalar numbers and nested JSON arrays/objects. |
| 8 | **Python Boolean Case-Sensitivity** | `json.loads("True")` failed on Python title-cased booleans, falling back to strings. | Added case-insensitive boolean checks (`raw.lower() in ("true", "false")`) and `ast.literal_eval`. |

---

## 4. Testcase Bundling & S3 Storage Architecture

To eliminate database bottlenecks on massive test suites:
- **Consolidated S3 Bundle Path**: `testcases/{problem_id}/bundle.json` or `testcases/{slug}/bundle.json`
- **Schema**:
  ```json
  {
    "method_name": "largestOverlap",
    "test_cases": [
      {
        "input": "[[1,1,0],[0,1,0],[0,1,0]]\n[[0,0,0],[0,1,1],[0,0,1]]",
        "expected_output": "3",
        "is_sample": true
      }
    ]
  }
  ```
- **Fallback**: If bundle doesn't exist in S3, automatically queries the PostgreSQL `test_cases` table.
- **First-Failed-Case Reporting (`FirstFailedTestCase`)**:
  - Stops processing on the first mismatch.
  - Captures `test_case_number`, `total_test_cases`, `input`, `expected_output`, `actual_output` (with safe 1,000-char truncation).
  - Displays directly in the frontend Verdict Modal and Workspace Console diff.

---

## 5. Database Schema & Data Models

### Tables
- **`users`**: UUID primary key, `cognito_sub` (unique index), `email`, `username`, `role` (`user` | `admin`), timestamps.
- **`problems`**: Integer ID, unique `slug`, `title`, `description`, `difficulty` (`easy`, `medium`, `hard`), `published` boolean.
- **`tags` & `problem_tags`**: Many-to-many relationship for categorization.
- **`problem_templates`**: Language-specific starter code and driver code placeholders.
- **`test_cases`**: Input, expected output, `is_sample` flag, linked to `problem_id`.
- **`submissions`**: UUID primary key, `user_id`, `problem_id`, `language`, `code`, `status`, `runtime_ms`, `memory_kb`, `passed_test_cases`, `total_test_cases`, `first_failed_case` (JSONB metadata).

---

## 6. Project Directory Structure

```
cloud_v3/
├── app/
│   ├── api/
│   │   ├── deps.py                      # DB sessions, JWT extraction, RBAC guards
│   │   └── v1/
│   │       ├── router.py                # Main API router
│   │       └── endpoints/
│   │           ├── auth.py              # Login, register, confirm, forgot-pwd, sync
│   │           ├── problems.py          # Problem CRUD, tags, templates
│   │           ├── submissions.py       # Submit code, poll verdict, history
│   │           └── users.py             # User stats and profiles
│   ├── core/
│   │   ├── config.py                    # Pydantic BaseSettings & env configs
│   │   ├── database.py                  # SQLAlchemy 2.0 async engine & sessionmaker
│   │   └── security.py                  # RS256 Cognito JWKS & HS256 JWT validators
│   ├── models/                          # SQLAlchemy ORM declarative models
│   ├── schemas/                         # Pydantic request/response schemas
│   ├── services/
│   │   ├── cache_service.py             # Redis caching for problem catalog & detail
│   │   ├── cognito_service.py           # AWS Cognito User Pool wrapper & mock engine
│   │   ├── harness_service.py           # Multi-language test harness code assembler
│   │   ├── judge0_service.py            # Judge0 REST client (runs & submissions)
│   │   └── s3_service.py                # S3 testcase bundle storage & retrieval
│   └── worker/
│       ├── celery_app.py                # Celery configuration
│       └── tasks.py                     # Async submission processing worker
├── frontend/
│   ├── src/
│   │   ├── api/                         # Axios client, authApi, problemApi, submissionApi
│   │   ├── components/
│   │   │   ├── LoginModal.tsx           # Full Cognito Auth Modal (Sign In/Register/OTP)
│   │   │   ├── Navbar.tsx               # Swiss minimalist top bar & user profile
│   │   │   ├── ProblemCatalog.tsx       # Searchable problem list with difficulty badges
│   │   │   ├── StatsModal.tsx           # Solved count, acceptance rate, chart
│   │   │   ├── VerdictModal.tsx         # Accepted / Wrong Answer / Error display
│   │   │   └── Workspace.tsx            # Monaco editor, testcase runner, console diff
│   │   ├── context/
│   │   │   └── AuthContext.tsx          # Global authentication state
│   │   ├── types/                       # TypeScript interfaces and types
│   │   └── App.tsx                      # Root component
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── conftest.py                      # Async HTTP test fixtures
│   ├── test_cognito_auth.py             # Cognito auth and RBAC unit tests
│   └── test_harness.py                  # Harness assembler & single-call tests
├── PROJECT_DETAILS.md                   # Complete system documentation (this file)
└── docker-compose.yml                   # Local infrastructure stack
```

---

## 7. Verification & Test Execution

### Backend Automated Test Suite
Run tests using the project virtual environment:
```powershell
.venv\Scripts\pytest tests/test_harness.py tests/test_cognito_auth.py -v
```
**Results**:
- `test_harness_custom_driver_substitution`: PASSED
- `test_harness_cpp_largest_overlap_generation`: PASSED
- `test_harness_python_default_wrapper`: PASSED
- `test_harness_java_largest_overlap_generation`: PASSED
- `test_harness_js_largest_overlap_generation`: PASSED
- `test_harness_output_parsing_and_json_matching`: PASSED
- `test_harness_method_name_support`: PASSED
- `test_harness_extract_first_failure_and_truncation`: PASSED
- `test_s3_bundle_storage_and_retrieval`: PASSED
- `test_bug1_stdin_desync_on_unmatched_signature`: PASSED
- `test_bug2_java_generic_parameters_bracket_splitting`: PASSED
- `test_bug3_type_parsing_and_fallback`: PASSED
- `test_bug4_zero_arg_void_methods`: PASSED
- `test_bug5_python_tuple_json_serialization`: PASSED
- `test_bug6_js_template_literal_injection`: PASSED
- `test_bug7_float_tolerance_in_outputs_match`: PASSED
- `test_bug8_python_boolean_case_insensitivity`: PASSED
- `test_cognito_service_direct_mock_flow`: PASSED
- `test_auth_api_config_endpoint`: PASSED
- `test_auth_api_login_endpoint`: PASSED
- `test_auth_api_admin_login_and_rbac`: PASSED
- `test_auth_api_user_forbidden_on_admin_check`: PASSED
**Total: 22 passed, 1 skipped** (live DB integration test skips cleanly when local PostgreSQL is offline).

### Frontend Production Build
```bash
cd frontend
npm run build
```
**Results**: 1,668 modules transformed, 0 TypeScript errors, production bundle generated cleanly in `dist/`.

---

## 8. Deployment & Environment Configuration

### Environment Variables (`.env`)
```env
ENVIRONMENT=production
DEBUG=False

# PostgreSQL (Amazon RDS or self-hosted)
DATABASE_URL=postgresql+asyncpg://user:password@rds-endpoint:5432/codegrid
SYNC_DATABASE_URL=postgresql://user:password@rds-endpoint:5432/codegrid

# Redis (Amazon ElastiCache or self-hosted)
REDIS_URL=redis://elasticache-endpoint:6379/0
CELERY_BROKER_URL=redis://elasticache-endpoint:6379/1
CELERY_RESULT_BACKEND=redis://elasticache-endpoint:6379/2

# AWS Cognito
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxxxxxx
MOCK_COGNITO=False

# AWS S3
S3_BUCKET_NAME=codegrid-problem-storage
MOCK_S3=False

# Judge0 Execution Cluster
MOCK_JUDGE0=False
JUDGE0_URL=http://judge0-server:2358
JUDGE0_CALLBACK_URL=https://api.yourdomain.com/internal/judge0-callback

# CORS Allowed Origins
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```
