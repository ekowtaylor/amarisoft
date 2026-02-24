"""Tests for service exceptions and error mapping."""

from __future__ import annotations

import pytest
from fastapi import status
from amarisoft.exceptions import (
    AmariConnectionError,
    AmariError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
    InvalidParameterError,
)
from service.exceptions import (
    APIError,
    BadRequestError,
    GatewayTimeoutError,
    InternalServerError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
    error_response,
    map_amarisoft_exception,
)


class TestAPIError:
    """Tests for APIError base class."""

    def test_api_error_attributes(self):
        error = APIError(
            status_code=400,
            error="Test error",
            detail="Test detail",
            error_code="TEST_ERROR",
        )
        assert error.status_code == 400
        assert error.error == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.detail == {
            "error": "Test error",
            "detail": "Test detail",
            "error_code": "TEST_ERROR",
        }


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError."""

    def test_default_message(self):
        error = ServiceUnavailableError(service="eNB")
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "eNB" in error.error
        assert error.error_code == "SERVICE_UNAVAILABLE"

    def test_custom_detail(self):
        error = ServiceUnavailableError(
            service="MME",
            detail="Connection refused",
        )
        assert "Connection refused" in error.detail["detail"]


class TestGatewayTimeoutError:
    """Tests for GatewayTimeoutError."""

    def test_default_message(self):
        error = GatewayTimeoutError()
        assert error.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert error.error_code == "GATEWAY_TIMEOUT"

    def test_custom_detail(self):
        error = GatewayTimeoutError(detail="Request took too long")
        assert "Request took too long" in error.detail["detail"]


class TestBadRequestError:
    """Tests for BadRequestError."""

    def test_with_detail(self):
        error = BadRequestError(detail="Invalid parameter")
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.error_code == "BAD_REQUEST"
        assert "Invalid parameter" in error.detail["detail"]

    def test_custom_error_code(self):
        error = BadRequestError(detail="Test", error_code="CUSTOM_CODE")
        assert error.error_code == "CUSTOM_CODE"


class TestUnauthorizedError:
    """Tests for UnauthorizedError."""

    def test_default_message(self):
        error = UnauthorizedError()
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "UNAUTHORIZED"

    def test_custom_detail(self):
        error = UnauthorizedError(detail="Invalid API key")
        assert "Invalid API key" in error.detail["detail"]


class TestValidationError:
    """Tests for ValidationError."""

    def test_with_detail(self):
        error = ValidationError(detail="Field 'name' is required")
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "VALIDATION_ERROR"
        assert "name" in error.detail["detail"]


class TestInternalServerError:
    """Tests for InternalServerError."""

    def test_default_message(self):
        error = InternalServerError()
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.error_code == "INTERNAL_ERROR"

    def test_custom_detail(self):
        error = InternalServerError(detail="Database error")
        assert "Database error" in error.detail["detail"]


class TestMapAmariException:
    """Tests for map_amarisoft_exception function."""

    def test_connection_error(self):
        exc = AmariConnectionError("Connection refused")
        result = map_amarisoft_exception(exc, "eNB")
        assert isinstance(result, ServiceUnavailableError)
        assert result.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_authentication_error(self):
        exc = AuthenticationError("Invalid password")
        result = map_amarisoft_exception(exc, "MME")
        assert isinstance(result, UnauthorizedError)
        assert result.status_code == status.HTTP_401_UNAUTHORIZED
        assert "MME" in result.detail["detail"]

    def test_timeout_error(self):
        exc = AmariTimeoutError("Request timed out")
        result = map_amarisoft_exception(exc, "IMS")
        assert isinstance(result, GatewayTimeoutError)
        assert result.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    def test_command_error(self):
        exc = CommandError("Unknown command", error_code=404)
        result = map_amarisoft_exception(exc, "UE")
        assert isinstance(result, BadRequestError)
        assert result.status_code == status.HTTP_400_BAD_REQUEST
        assert result.error_code == 404

    def test_command_error_no_code(self):
        exc = CommandError("Unknown command")
        result = map_amarisoft_exception(exc)
        assert isinstance(result, BadRequestError)

    def test_invalid_parameter_error(self):
        exc = InvalidParameterError("Invalid gain value")
        result = map_amarisoft_exception(exc)
        assert isinstance(result, ValidationError)
        assert result.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_generic_amari_error(self):
        exc = AmariError("Unknown error")
        result = map_amarisoft_exception(exc, "Service")
        assert isinstance(result, InternalServerError)
        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestErrorResponse:
    """Tests for error_response helper function."""

    def test_minimal_response(self):
        result = error_response("Test error")
        assert result == {"error": "Test error"}

    def test_with_detail(self):
        result = error_response("Test error", detail="More info")
        assert result == {
            "error": "Test error",
            "detail": "More info",
        }

    def test_with_error_code(self):
        result = error_response("Test error", error_code="TEST_001")
        assert result == {
            "error": "Test error",
            "error_code": "TEST_001",
        }

    def test_full_response(self):
        result = error_response(
            "Test error",
            detail="More info",
            error_code="TEST_001",
        )
        assert result == {
            "error": "Test error",
            "detail": "More info",
            "error_code": "TEST_001",
        }
