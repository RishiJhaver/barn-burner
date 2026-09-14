export type UserRole = 'user' | 'admin';
export type ProblemDifficulty = 'easy' | 'medium' | 'hard';
export type SubmissionKind = 'run' | 'submit';
export type SubmissionStatus =
  | 'pending'
  | 'processing'
  | 'accepted'
  | 'wrong_answer'
  | 'time_limit_exceeded'
  | 'memory_limit_exceeded'
  | 'runtime_error'
  | 'compilation_error'
  | 'internal_error';

export type SupportedLanguage = 'python' | 'cpp' | 'java' | 'javascript';

export interface User {
  id: string;
  cognito_sub?: string;
  email: string;
  username: string;
  role: UserRole;
  created_at: string;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
}

export interface ProblemTemplate {
  id: number;
  problem_id: number;
  language: string;
  starter_code: string;
  driver_code?: string | null;
}

export interface TestCase {
  id?: number;
  input: string;
  expected_output: string;
  is_sample: boolean;
}

export interface Problem {
  id: number;
  slug: string;
  title: string;
  description: string;
  difficulty: ProblemDifficulty;
  published: boolean;
  created_at: string;
  tags: Tag[];
  templates?: ProblemTemplate[];
  sample_test_cases?: TestCase[];
  solve_status?: 'solved' | 'attempted' | 'unsolved';
}

export interface SubmissionAcceptedResponse {
  submission_id: string;
  status: SubmissionStatus;
  kind: SubmissionKind;
  created_at: string;
}

export interface TestCaseExecutionResult {
  test_case_id: number;
  status: string;
  runtime_ms: number;
  memory_kb: number;
  stdin?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  error_message?: string | null;
}

export interface FirstFailedTestCase {
  test_case_number: number;
  total_test_cases: number;
  input: string;
  expected_output: string;
  actual_output: string;
}

export interface SubmissionDetail {
  id: string;
  user_id: string;
  problem_id: number;
  problem_slug?: string | null;
  problem_title?: string | null;
  language: string;
  kind: SubmissionKind;
  status: SubmissionStatus;
  runtime_ms?: number | null;
  memory_kb?: number | null;
  error_message?: string | null;
  passed_test_cases?: number | null;
  total_test_cases?: number | null;
  sample_results?: TestCaseExecutionResult[] | null;
  first_failed_case?: FirstFailedTestCase | null;
  created_at: string;
  updated_at: string;
}

export interface UserStats {
  total_submissions: number;
  accepted_submissions: number;
  acceptance_rate: number;
  easy_solved: number;
  medium_solved: number;
  hard_solved: number;
  total_solved: number;
}

export interface AuthConfig {
  mock_cognito: boolean;
  aws_region: string;
  user_pool_id: string;
  client_id?: string;
  cognito_domain?: string;
  oauth_url?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  role: UserRole;
}

export interface SignUpResponse {
  user_sub?: string;
  user_confirmed: boolean;
  delivery_medium: string;
  destination?: string;
  demo_hint?: string;
}

