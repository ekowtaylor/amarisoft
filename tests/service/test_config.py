"""Tests for service configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from service.config import Settings, get_settings, _get_bool_env, _get_int_env, _get_float_env


class TestEnvParsers:
    """Tests for environment variable parsing helpers."""

    def test_get_bool_env_true_values(self):
        with patch.dict(os.environ, {"TEST_VAR": "true"}):
            assert _get_bool_env("TEST_VAR") is True
        with patch.dict(os.environ, {"TEST_VAR": "1"}):
            assert _get_bool_env("TEST_VAR") is True
        with patch.dict(os.environ, {"TEST_VAR": "yes"}):
            assert _get_bool_env("TEST_VAR") is True
        with patch.dict(os.environ, {"TEST_VAR": "on"}):
            assert _get_bool_env("TEST_VAR") is True

    def test_get_bool_env_false_values(self):
        with patch.dict(os.environ, {"TEST_VAR": "false"}):
            assert _get_bool_env("TEST_VAR") is False
        with patch.dict(os.environ, {"TEST_VAR": "0"}):
            assert _get_bool_env("TEST_VAR") is False
        with patch.dict(os.environ, {"TEST_VAR": "no"}):
            assert _get_bool_env("TEST_VAR") is False
        with patch.dict(os.environ, {"TEST_VAR": "off"}):
            assert _get_bool_env("TEST_VAR") is False

    def test_get_bool_env_default(self):
        assert _get_bool_env("NONEXISTENT_VAR", default=True) is True
        assert _get_bool_env("NONEXISTENT_VAR", default=False) is False

    def test_get_bool_env_invalid_returns_default(self):
        with patch.dict(os.environ, {"TEST_VAR": "invalid"}):
            assert _get_bool_env("TEST_VAR", default=True) is True
            assert _get_bool_env("TEST_VAR", default=False) is False

    def test_get_int_env(self):
        with patch.dict(os.environ, {"TEST_VAR": "42"}):
            assert _get_int_env("TEST_VAR", 0) == 42

    def test_get_int_env_default(self):
        assert _get_int_env("NONEXISTENT_VAR", 99) == 99

    def test_get_int_env_invalid_returns_default(self):
        with patch.dict(os.environ, {"TEST_VAR": "not_a_number"}):
            assert _get_int_env("TEST_VAR", 99) == 99

    def test_get_float_env(self):
        with patch.dict(os.environ, {"TEST_VAR": "3.14"}):
            assert _get_float_env("TEST_VAR", 0.0) == 3.14

    def test_get_float_env_default(self):
        assert _get_float_env("NONEXISTENT_VAR", 1.5) == 1.5

    def test_get_float_env_invalid_returns_default(self):
        with patch.dict(os.environ, {"TEST_VAR": "not_a_float"}):
            assert _get_float_env("TEST_VAR", 1.5) == 1.5


class TestSettings:
    """Tests for Settings dataclass."""

    def test_default_values(self):
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 9010
        assert settings.callbox_host == "127.0.0.1"
        assert settings.enb_port == 9001
        assert settings.mme_port == 9000
        assert settings.ims_port == 9002
        assert settings.ue_port == 9003
        assert settings.ws_timeout == 10.0
        assert settings.ws_password is None
        assert settings.auto_reconnect is True
        assert settings.ssl is False
        assert settings.ssl_verify is False
        assert settings.api_key is None
        assert settings.enable_cors is True
        assert settings.log_level == "INFO"

    def test_custom_values(self):
        settings = Settings(
            host="192.168.1.100",
            port=8080,
            callbox_host="10.0.0.1",
            ws_password="secret",
            api_key="my-api-key",
            log_level="DEBUG",
        )
        assert settings.host == "192.168.1.100"
        assert settings.port == 8080
        assert settings.callbox_host == "10.0.0.1"
        assert settings.ws_password == "secret"
        assert settings.api_key == "my-api-key"
        assert settings.log_level == "DEBUG"

    def test_settings_is_frozen(self):
        settings = Settings()
        with pytest.raises(Exception):  # FrozenInstanceError
            settings.port = 9999

    def test_from_env(self):
        env_vars = {
            "AMARISOFT_API_HOST": "10.0.0.1",
            "AMARISOFT_API_PORT": "8080",
            "AMARISOFT_CALLBOX_HOST": "192.168.1.100",
            "AMARISOFT_ENB_PORT": "9011",
            "AMARISOFT_MME_PORT": "9010",
            "AMARISOFT_IMS_PORT": "9012",
            "AMARISOFT_UE_PORT": "9013",
            "AMARISOFT_WS_TIMEOUT": "30.0",
            "AMARISOFT_WS_PASSWORD": "secret123",
            "AMARISOFT_API_KEY": "api-key-123",
            "AMARISOFT_ENABLE_CORS": "false",
            "AMARISOFT_LOG_LEVEL": "debug",
            "AMARISOFT_AUTO_RECONNECT": "false",
            "AMARISOFT_WS_SSL": "true",
            "AMARISOFT_WS_SSL_VERIFY": "true",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings.from_env()

        assert settings.host == "10.0.0.1"
        assert settings.port == 8080
        assert settings.callbox_host == "192.168.1.100"
        assert settings.enb_port == 9011
        assert settings.mme_port == 9010
        assert settings.ims_port == 9012
        assert settings.ue_port == 9013
        assert settings.ws_timeout == 30.0
        assert settings.ws_password == "secret123"
        assert settings.api_key == "api-key-123"
        assert settings.enable_cors is False
        assert settings.log_level == "DEBUG"
        assert settings.auto_reconnect is False
        assert settings.ssl is True
        assert settings.ssl_verify is True

    def test_from_env_cors_origins(self):
        env_vars = {
            "AMARISOFT_CORS_ORIGINS": "http://localhost:3000,https://example.com",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings.from_env()

        assert settings.cors_origins == ("http://localhost:3000", "https://example.com")

    def test_get_service_ports(self):
        settings = Settings()
        ports = settings.get_service_ports()
        assert ports == {
            "enb": 9001,
            "mme": 9000,
            "ims": 9002,
            "ue": 9003,
        }


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings(self):
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self):
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_cache_clear(self):
        get_settings.cache_clear()
        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()
        # They should be equal but not the same object
        assert settings1 == settings2
