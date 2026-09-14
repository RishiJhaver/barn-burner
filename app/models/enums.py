import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class ProblemDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubmissionKind(str, enum.Enum):
    RUN = "run"
    SUBMIT = "submit"


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILATION_ERROR = "compilation_error"
    INTERNAL_ERROR = "internal_error"


class ProblemSolveStatus(str, enum.Enum):
    ATTEMPTED = "attempted"
    SOLVED = "solved"
