"""Custom exceptions. Each one maps to an HTTP status code in main.py."""


class AppError(Exception):
    status_code = 500

    def __init__(self, message: str = "Application error"):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400


class ResumeProcessingError(ValidationError):
    """Invalid / unreadable PDF."""


class AuthError(AppError):
    status_code = 401


class PermissionDenied(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class LLMUnavailableError(AppError):
    status_code = 503


class VectorStoreError(AppError):
    status_code = 500


class DatabaseError(AppError):
    status_code = 500
