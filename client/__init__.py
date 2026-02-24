"""Amarisoft Client Libraries.

This package provides two client interfaces for Amarisoft Callbox:

- **websocket**: Direct WebSocket client library for local/low-latency access
- **http**: HTTP REST API client for remote access via the REST service

WebSocket Client (client.websocket)
-----------------------------------
Use when running directly on or near the callbox for maximum performance::

    from client.websocket import Callbox

    with Callbox("192.168.1.80") as cb:
        stats = cb.enb.stats()

HTTP Client (client.http)
-------------------------
Use when accessing the callbox remotely via the REST API service::

    import requests
    response = requests.get("http://192.168.1.80:9010/enb/stats")
    stats = response.json()

See examples/websocket/ and examples/http/ for more usage examples.
"""

__version__ = "0.1.0"
