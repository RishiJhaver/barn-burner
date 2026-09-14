-- LeetCode Clone PostgreSQL Schema
-- Generated according to architecture specification

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enums
CREATE TYPE user_role AS ENUM ('user', 'admin');
CREATE TYPE problem_difficulty AS ENUM ('easy', 'medium', 'hard');
CREATE TYPE submission_kind AS ENUM ('run', 'submit');
CREATE TYPE submission_status AS ENUM (
    'pending',
    'processing',
    'accepted',
    'wrong_answer',
    'time_limit_exceeded',
    'memory_limit_exceeded',
    'runtime_error',
    'compilation_error',
    'internal_error'
);
CREATE TYPE problem_solve_status AS ENUM ('attempted', 'solved');

-- 1. Users Table
-- UUID PK to avoid enumeration attacks and align with external auth providers (Cognito sub)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_cognito_sub ON users (cognito_sub);
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_username ON users (username);

-- 2. Problems Table
-- Serial integer PK for compact foreign keys and efficient B-tree indexing
CREATE TABLE problems (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(128) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    difficulty problem_difficulty NOT NULL,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Keyset pagination index on published problems
CREATE INDEX idx_problems_published_created ON problems (published, created_at DESC, id DESC);
CREATE INDEX idx_problems_slug ON problems (slug);

-- 3. Tags Table
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    slug VARCHAR(64) NOT NULL UNIQUE
);

-- 4. Problem Tags Junction Table
CREATE TABLE problem_tags (
    problem_id INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    tag_id INT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (problem_id, tag_id)
);

CREATE INDEX idx_problem_tags_tag_id ON problem_tags (tag_id);

-- 5. Problem Templates (Starter code per language)
CREATE TABLE problem_templates (
    id SERIAL PRIMARY KEY,
    problem_id INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    language VARCHAR(32) NOT NULL,
    starter_code TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_problem_language UNIQUE (problem_id, language)
);

CREATE INDEX idx_problem_templates_problem_id ON problem_templates (problem_id);

-- 6. Test Cases (Sample visible vs Hidden full suite)
CREATE TABLE test_cases (
    id SERIAL PRIMARY KEY,
    problem_id INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    input TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_sample BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial index for fast retrieval of sample test cases for GET /problems/{slug} and 'run' endpoint
CREATE INDEX idx_test_cases_sample ON test_cases (problem_id) WHERE is_sample = TRUE;
CREATE INDEX idx_test_cases_problem_id ON test_cases (problem_id);

-- 7. Submissions Table
-- UUID PK to prevent submission enumeration across users
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    language VARCHAR(32) NOT NULL,
    code TEXT NOT NULL,
    kind submission_kind NOT NULL DEFAULT 'submit',
    status submission_status NOT NULL DEFAULT 'pending',
    runtime_ms INT NULL,
    memory_kb INT NULL,
    error_message TEXT NULL,
    judge0_token VARCHAR(64) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial index: submission history only needs 'submit' entries (can exclude ephemeral 'run' submissions)
CREATE INDEX idx_submissions_user_history ON submissions (user_id, created_at DESC) WHERE kind = 'submit';
CREATE INDEX idx_submissions_user_problem ON submissions (user_id, problem_id, created_at DESC);
CREATE INDEX idx_submissions_judge0_token ON submissions (judge0_token) WHERE judge0_token IS NOT NULL;

-- 8. User Problem Status Table
-- Tracks whether a user has attempted or solved a problem
CREATE TABLE user_problem_status (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    status problem_solve_status NOT NULL DEFAULT 'attempted',
    last_submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, problem_id)
);

CREATE INDEX idx_user_problem_status_user_id ON user_problem_status (user_id);
