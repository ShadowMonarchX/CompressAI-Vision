class DomainError(Exception):
    status_code = 400
    code = "domain_error"
    def __init__(self, message: str): super().__init__(message); self.message = message
class JobNotFoundError(DomainError): status_code, code = 404, "job_not_found"
class FileTooLargeError(DomainError): status_code, code = 413, "file_too_large"
class MediaTypeError(DomainError): status_code, code = 415, "unsupported_media_type"
class ServiceUnavailableError(DomainError): status_code, code = 503, "service_unavailable"
