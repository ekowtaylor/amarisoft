"""HTTP exception mappings for Amarisoft REST API.

Maps Amarisoft WebSocket exceptions to appropriate HTTP status codes
and provides structured error responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from client.websocket.exceptions import (
    AmariConnectionError,
    AmariError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
    InvalidParameterError,
)


class APIError(HTTPException):
    """Base API error with structured error response."""

    def __init__(
        self,
        status_code: int,
        error: str,
        detail: str | None = None,
        error_code: str | int | None = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": error,
                "detail": detail,
                "error_code": error_code,
            },
        )
        self.error = error
        self.error_code = error_code


class ServiceUnavailableError(APIError):
    """Raised when a backend Amarisoft service is unavailable."""

    def __init__(self, service: str, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error=f"{service} service unavailable",
            detail=detail or f"Cannot connect to {service} WebSocket service",
            error_code="SERVICE_UNAVAILABLE",
        )


class GatewayTimeoutError(APIError):
    """Raised when a backend service request times out."""

    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error="Gateway timeout",
            detail=detail or "Backend service did not respond in time",
            error_code="GATEWAY_TIMEOUT",
        )


class BadRequestError(APIError):
    """Raised when the request contains invalid parameters."""

    def __init__(self, detail: str, error_code: str | int | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="Bad request",
            detail=detail,
            error_code=error_code or "BAD_REQUEST",
        )


class UnauthorizedError(APIError):
    """Raised when authentication fails."""

    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="Unauthorized",
            detail=detail or "Authentication required",
            error_code="UNAUTHORIZED",
        )


class ValidationError(APIError):
    """Raised when request validation fails."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="Validation error",
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class InternalServerError(APIError):
    """Raised for unexpected internal errors."""

    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="Internal server error",
            detail=detail or "An unexpected error occurred",
            error_code="INTERNAL_ERROR",
        )


def map_amarisoft_exception(exc: AmariError, service: str = "Amarisoft") -> APIError:
    """Map an Amarisoft exception to an appropriate HTTP API error.

    Args:
        exc: The Amarisoft exception to map.
        service: Name of the service for context in error messages.

    Returns:
        An appropriate APIError subclass.
    """
    if isinstance(exc, AmariConnectionError):
        return ServiceUnavailableError(
            service=service,
            detail=str(exc),
        )

    if isinstance(exc, AuthenticationError):
        return UnauthorizedError(
            detail=f"{service} authentication failed: {exc}",
        )

    if isinstance(exc, AmariTimeoutError):
        return GatewayTimeoutError(
            detail=f"{service} request timed out: {exc}",
        )

    if isinstance(exc, CommandError):
        return BadRequestError(
            detail=str(exc),
            error_code=exc.error_code,
        )

    if isinstance(exc, InvalidParameterError):
        return ValidationError(
            detail=str(exc),
        )

    # Fallback for unknown AmariError subclasses
    return InternalServerError(
        detail=f"{service} error: {exc}",
    )


def error_response(
    error: str,
    detail: str | None = None,
    error_code: str | int | None = None,
) -> dict[str, Any]:
    """Create a structured error response dictionary.

    Useful for creating error responses without raising exceptions.

    Args:
        error: Short error description.
        detail: Detailed error message.
        error_code: Machine-readable error code.

    Returns:
        Error response dictionary.
    """
    response: dict[str, Any] = {"error": error}
    if detail:
        response["detail"] = detail
    if error_code:
        response["error_code"] = error_code
    return response
