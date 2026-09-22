class HttpClientError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class HttpTimeoutError(HttpClientError):
    def __init__(self, message: str = "HTTP request timed out") -> None:
        super().__init__(message, retryable=True)


class HttpConnectionError(HttpClientError):
    def __init__(self, message: str = "HTTP connection failed") -> None:
        super().__init__(message, retryable=True)


class HttpStatusError(HttpClientError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        retryable: bool,
    ) -> None:
        super().__init__(message, retryable=retryable)
        self.status_code = status_code


def is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 429, 500, 502, 503, 504}
