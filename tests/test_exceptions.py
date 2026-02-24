"""Tests for the exception hierarchy."""

from client.websocket.exceptions import (
    AmariConnectionError,
    AmariError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
    InvalidParameterError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_amari_error(self):
        for cls in (
            AmariConnectionError,
            AuthenticationError,
            AmariTimeoutError,
            CommandError,
            InvalidParameterError,
        ):
            assert issubclass(cls, AmariError)

    def test_amari_error_is_exception(self):
        assert issubclass(AmariError, Exception)

    def test_command_error_stores_error_code(self):
        err = CommandError("bad", error_code=42)
        assert str(err) == "bad"
        assert err.error_code == 42

    def test_command_error_default_error_code_is_none(self):
        err = CommandError("oops")
        assert err.error_code is None

    def test_no_builtin_shadowing(self):
        """Custom names should not shadow Python builtins."""
        import builtins
        for name in (
            "AmariError",
            "AmariConnectionError",
            "AuthenticationError",
            "AmariTimeoutError",
            "CommandError",
            "InvalidParameterError",
        ):
            assert not hasattr(builtins, name)
