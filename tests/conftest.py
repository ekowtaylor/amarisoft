"""Shared fixtures for the Amarisoft test suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from client.websocket.client import WebSocketClient
from client.websocket.enb import ENBApi
from client.websocket.mme import MMEApi
from client.websocket.ims import IMSApi
from client.websocket.ue import UEApi


@pytest.fixture()
def mock_client():
    """Return a WebSocketClient with ``send()`` mocked.

    The mock stores the sent message on ``mock_client.last_sent`` and
    returns ``{"message_id": N}`` where *N* matches the ``message_id``
    injected by the real ``send()`` — but since ``send()`` itself is
    mocked we simply echo whatever the caller provides.
    """
    client = MagicMock(spec=WebSocketClient)

    def _send(msg):
        client.last_sent = msg
        return {"message_id": msg.get("message_id", 1)}

    client.send.side_effect = _send
    client.send_raw.side_effect = lambda msg: {"message_id": 0}
    client.send_batch.side_effect = lambda msgs: [
        {"message_id": m.get("message_id", i)} for i, m in enumerate(msgs)
    ]
    return client


@pytest.fixture()
def enb(mock_client):
    return ENBApi(mock_client)


@pytest.fixture()
def mme(mock_client):
    return MMEApi(mock_client)


@pytest.fixture()
def ims(mock_client):
    return IMSApi(mock_client)


@pytest.fixture()
def ue(mock_client):
    return UEApi(mock_client)
