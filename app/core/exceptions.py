"""Application-domain exceptions exposed as structured API errors."""

from typing import ClassVar


class DomainError(Exception):
    """Base exception for expected application failures."""

    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "domain_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class JobNotFoundError(DomainError):
    """Raised when a requested job does not exist or is not ready."""

    status_code: ClassVar[int] = 404
    code: ClassVar[str] = "job_not_found"


class FileTooLargeError(DomainError):
    """Raised when an uploaded file exceeds the configured limit."""

    status_code: ClassVar[int] = 413
    code: ClassVar[str] = "file_too_large"


class MediaTypeError(DomainError):
    """Raised when an uploaded media type is not supported."""

    status_code: ClassVar[int] = 415
    code: ClassVar[str] = "unsupported_media_type"


class ServiceUnavailableError(DomainError):
    """Raised when a required local or external service is unavailable."""

    status_code: ClassVar[int] = 503
    code: ClassVar[str] = "service_unavailable"
