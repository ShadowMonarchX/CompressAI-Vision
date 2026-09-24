"""Application-domain exceptions exposed as structured API errors."""

from typing import ClassVar


class AppError(Exception):
    """Base exception for expected application failures."""

    status_code: ClassVar[int] = 400
    error_code: ClassVar[str] = "internal_error"

    def __init__(self, message: str, **context) -> None:
        self.message, self.context = message, context
        super().__init__(message)


class DomainError(AppError):
    """Backward-compatible base for expected failures."""

class JobNotFoundError(AppError):
    """Raised when a requested job does not exist or is not ready."""

    status_code: ClassVar[int] = 404
    error_code: ClassVar[str] = "job_not_found"


class FileTooLargeError(AppError):
    """Raised when an uploaded file exceeds the configured limit."""

    status_code: ClassVar[int] = 413
    error_code: ClassVar[str] = "file_too_large"


class UnsupportedMediaTypeError(AppError):
    """Raised when an uploaded media type is not supported."""

    status_code: ClassVar[int] = 415
    error_code: ClassVar[str] = "unsupported_media_type"


class MediaTypeError(UnsupportedMediaTypeError): pass
class ChecksumMismatchError(AppError): status_code=400; error_code="checksum_mismatch"
class JobNotDoneError(AppError): status_code=409; error_code="job_not_done"
class InvalidJobStateTransitionError(AppError): status_code=409; error_code="invalid_job_state_transition"
class InsufficientDiskSpaceError(AppError): status_code=507; error_code="insufficient_disk_space"
class CompressionFailedError(AppError): status_code=422; error_code="compression_failed"
class FFmpegNotAvailableError(AppError): status_code=503; error_code="ffmpeg_not_available"
class FFmpegTimeoutError(AppError): status_code=504; error_code="ffmpeg_timeout"
class QualityThresholdUnreachableError(AppError): status_code=422; error_code="quality_threshold_unreachable"
class RateLimitExceededError(AppError): status_code=429; error_code="rate_limit_exceeded"
class InvalidConfigurationError(AppError): status_code=500; error_code="invalid_configuration"
class StorageError(AppError): status_code=500; error_code="storage_error"
class ServiceUnavailableError(FFmpegNotAvailableError):
    """Raised when a required local or external service is unavailable."""

    status_code: ClassVar[int] = 503
    error_code: ClassVar[str] = "service_unavailable"
