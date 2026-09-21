from __future__ import annotations


class MaxApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: object = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class MaxApiAuthError(MaxApiError):
    pass


class MaxApiClientError(MaxApiError):
    pass


class MaxApiServerError(MaxApiError):
    pass


class MaxApiNetworkError(MaxApiError):
    pass
