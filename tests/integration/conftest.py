"""Shared fixtures and CLI options for integration tests."""

import pytest

from client.websocket import Callbox


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a live Callbox",
    )


def pytest_addoption(parser):
    parser.addoption(
        "--host",
        action="store",
        default="127.0.0.1",
        help="Callbox IP address (default: 127.0.0.1)",
    )
    parser.addoption(
        "--password",
        action="store",
        default=None,
        help="Authentication password",
    )
    parser.addoption(
        "--ssl",
        action="store_true",
        default=False,
        help="Use WSS (TLS)",
    )
    parser.addoption(
        "--ssl-verify",
        action="store_true",
        default=False,
        help="Verify TLS certificates (default: no verification)",
    )


@pytest.fixture(scope="session")
def callbox_host(request):
    return request.config.getoption("--host")


@pytest.fixture(scope="session")
def callbox_password(request):
    return request.config.getoption("--password")


@pytest.fixture(scope="session")
def callbox_ssl(request):
    return request.config.getoption("--ssl")


@pytest.fixture(scope="session")
def callbox_ssl_verify(request):
    return request.config.getoption("--ssl-verify")


@pytest.fixture(scope="session")
def callbox(callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify):
    """Session-scoped Callbox connected to all services."""
    cb = Callbox(
        callbox_host,
        password=callbox_password,
        ssl=callbox_ssl,
        ssl_verify=callbox_ssl_verify,
    )
    cb.connect_all()
    yield cb
    cb.close()


@pytest.fixture(scope="session")
def callbox_factory(callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify):
    """Factory fixture that creates unconnected Callbox instances."""
    instances = []

    def _make(**overrides):
        kwargs = {
            "host": callbox_host,
            "password": callbox_password,
            "ssl": callbox_ssl,
            "ssl_verify": callbox_ssl_verify,
        }
        kwargs.update(overrides)
        host = kwargs.pop("host")
        cb = Callbox(host, **kwargs)
        instances.append(cb)
        return cb

    yield _make

    for cb in instances:
        cb.close()
