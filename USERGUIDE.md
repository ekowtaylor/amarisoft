# Amarisoft Client Library - User Guide

This guide covers all client functions, parameters, usage examples, expected outputs, and API endpoints for the Amarisoft client library.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [HTTPClient](#httpclient)
- [WebSocketClient](#websocketclient)
- [HTTPOverSSHClient](#httpoversshclient)
- [API Endpoints Reference](#api-endpoints-reference)
  - [System Endpoints](#system-endpoints)
  - [eNB/gNB Endpoints](#enbgnb-endpoints)
  - [MME/AMF Endpoints](#mmeamf-endpoints)
  - [UE Simulator Endpoints](#ue-simulator-endpoints)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Overview

The Amarisoft client library provides three client types for communicating with Amarisoft services:

| Client | Use Case | Protocol |
|--------|----------|----------|
| `HTTPClient` | Direct REST API access | HTTP/HTTPS |
| `WebSocketClient` | Real-time communication with Amarisoft services | WebSocket |
| `HTTPOverSSHClient` | REST API access via SSH tunnel | HTTP over SSH |

---

## Installation

```bash
pip install requests websocket-client
# For HTTPOverSSHClient with password auth:
# Linux: apt-get install sshpass
# macOS: brew install hudochenkov/sshpass/sshpass
```

---

## HTTPClient

Low-level HTTP client for the Amarisoft REST API.

### Import

```python
from client.http import HTTPClient
```

### Constructor

```python
HTTPClient(
    base_url: str,
    timeout: float = 30.0,
    retries: int = 3,
    api_key: str | None = None,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | *required* | Base URL of the REST API (e.g., `"http://192.168.1.80:9010"`) |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `retries` | `int` | `3` | Number of retries for failed requests |
| `api_key` | `str \| None` | `None` | Optional API key for authentication |

### Methods

#### `is_listening(timeout: float = 2.0) -> bool`

Check if the HTTP service is listening (lightweight TCP check).

```python
client = HTTPClient("http://192.168.1.80:9010")

if client.is_listening():
    print("Service is available")
else:
    print("Service is not reachable")
```

**Parameters:**
- `timeout` (float): Connection timeout in seconds (default: 2.0)

**Returns:** `True` if service is listening, `False` otherwise

---

#### `get(endpoint: str, params: dict | None = None) -> dict`

Make a GET request.

```python
client = HTTPClient("http://192.168.1.80:9010")

# Simple GET
response = client.get("/health")
# Output: {"status": "healthy", "version": "2024-06-01", "timestamp": "..."}

# GET with query parameters
response = client.get("/enb/stats", params={"samples": True, "rf": True})
# Output: {"cells": [...], "ues": [...], ...}
```

**Parameters:**
- `endpoint` (str): API endpoint (e.g., `"/enb/stats"`)
- `params` (dict | None): Optional query parameters

**Returns:** JSON response as dictionary

**Raises:**
- `ConnectionError`: If connection fails
- `TimeoutError`: If request times out
- `APIError`: If API returns an error (4xx/5xx)

---

#### `post(endpoint: str, data: dict | None = None, params: dict | None = None) -> dict`

Make a POST request.

```python
# Activate a cell
response = client.post("/enb/cells/1/activate")
# Output: {"message": "cell_activate", "cell_id": 1}

# Create PDN connection
response = client.post("/mme/ue/1/pdn", data={
    "apn": "internet",
    "pdn_type": "ipv4"
})
# Output: {"message": "pdn_connect", "pdn_id": 5}
```

**Parameters:**
- `endpoint` (str): API endpoint
- `data` (dict | None): Request body data (sent as JSON)
- `params` (dict | None): Optional query parameters

**Returns:** JSON response as dictionary

---

#### `put(endpoint: str, data: dict | None = None) -> dict`

Make a PUT request.

```python
# Update configuration
response = client.put("/enb/config", data={
    "tx_gain": 80,
    "rx_gain": 40
})
# Output: {"message": "config_set"}
```

**Parameters:**
- `endpoint` (str): API endpoint
- `data` (dict | None): Request body data

**Returns:** JSON response as dictionary

---

#### `delete(endpoint: str, params: dict | None = None) -> dict`

Make a DELETE request.

```python
# Disconnect PDN
response = client.delete("/mme/ue/1/pdn/5")
# Output: {"message": "pdn_disconnect"}

# Delete bearer
response = client.delete("/mme/ue/1/bearer/6")
# Output: {"message": "bearer_deactivate"}
```

**Parameters:**
- `endpoint` (str): API endpoint
- `params` (dict | None): Optional query parameters

**Returns:** JSON response as dictionary

---

#### `health_check() -> dict`

Check if the REST API service is healthy.

```python
response = client.health_check()
# Output: {
#     "status": "healthy",
#     "timestamp": "2024-06-01T12:00:00Z",
#     "version": "1.0.0",
#     "callbox": {
#         "host": "192.168.1.80",
#         "connected_services": 4,
#         "total_services": 4
#     }
# }
```

**Returns:** Health status response

---

#### `close()`

Close the HTTP session.

```python
client.close()
```

---

### Context Manager Usage

```python
with HTTPClient("http://192.168.1.80:9010") as client:
    response = client.get("/health")
    print(response)
# Session automatically closed
```

---

## WebSocketClient

WebSocket client for real-time communication with Amarisoft services (eNB, MME, IMS, UE).

### Import

```python
from client.websocket import WebSocketClient
```

### Constructor

```python
WebSocketClient(
    host: str = "127.0.0.1",
    port: int = 9001,
    password: str | None = None,
    ssl: bool = False,
    timeout: float = 10.0,
    ssl_context: ssl.SSLContext | None = None,
    auto_reconnect: bool = False,
    ssl_verify: bool = False,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | `"127.0.0.1"` | Hostname or IP of the Amarisoft service |
| `port` | `int` | `9001` | WebSocket port |
| `password` | `str \| None` | `None` | Authentication password (com_auth) |
| `ssl` | `bool` | `False` | Use `wss://` instead of `ws://` |
| `timeout` | `float` | `10.0` | Default timeout in seconds |
| `ssl_context` | `SSLContext \| None` | `None` | Custom SSL context for TLS |
| `auto_reconnect` | `bool` | `False` | Automatically reconnect on send failure |
| `ssl_verify` | `bool` | `False` | Verify server's TLS certificate |

### Default Ports

| Service | Default Port |
|---------|-------------|
| MME/AMF | 9000 |
| eNB/gNB | 9001 |
| IMS | 9002 |
| UE Simulator | 9003 |

### Properties

#### `uri -> str`

Get the WebSocket URI.

```python
client = WebSocketClient(host="192.168.1.80", port=9001)
print(client.uri)
# Output: "ws://192.168.1.80:9001"

client = WebSocketClient(host="192.168.1.80", port=9001, ssl=True)
print(client.uri)
# Output: "wss://192.168.1.80:9001"
```

#### `connected -> bool`

Check if WebSocket is connected.

```python
print(client.connected)
# Output: False (before connect)

client.connect()
print(client.connected)
# Output: True
```

### Methods

#### `is_listening(timeout: float = 2.0) -> bool`

Check if the WebSocket service is listening (lightweight TCP check).

```python
client = WebSocketClient(host="192.168.1.80", port=9001)

if client.is_listening():
    print("eNB WebSocket service is available")
    client.connect()
else:
    print("Service not reachable")
```

**Parameters:**
- `timeout` (float): Connection timeout in seconds (default: 2.0)

**Returns:** `True` if service is listening, `False` otherwise

---

#### `connect() -> dict`

Establish WebSocket connection and wait for ready message.

```python
client = WebSocketClient(host="192.168.1.80", port=9001)
ready = client.connect()
# Output: {"message": "ready", "name": "lteenb", "version": "2024-06-01", ...}
```

**Returns:** The `ready` message from the server

**Raises:**
- `AmariConnectionError`: If connection cannot be established
- `AuthenticationError`: If authentication fails
- `AmariTimeoutError`: If no ready message received in time

---

#### `reconnect() -> dict`

Close and re-establish the connection.

```python
ready = client.reconnect()
# Output: {"message": "ready", ...}
```

**Returns:** The `ready` message from the server

---

#### `close()`

Close the WebSocket connection.

```python
client.close()
```

---

#### `send(message: dict) -> dict`

Send a JSON message and return the matching response.

```python
client = WebSocketClient(host="192.168.1.80", port=9001)
client.connect()

# Get eNB stats
response = client.send({"message": "stats"})
# Output: {
#     "message": "stats",
#     "message_id": 1,
#     "cells": [...],
#     "ues": [...]
# }

# Get config
response = client.send({"message": "config_get"})
# Output: {"message": "config_get", "message_id": 2, "rf_driver": {...}, ...}
```

**Parameters:**
- `message` (dict): The message dictionary to send

**Returns:** The parsed JSON response from the server

**Raises:**
- `AmariConnectionError`: If not connected or connection lost
- `CommandError`: If the server returns an error
- `AmariTimeoutError`: If no response received in time

---

#### `send_raw(message: dict) -> dict`

Send a message without adding a `message_id`.

```python
response = client.send_raw({"message": "config_get"})
# Output: {"message": "config_get", ...}
```

**Parameters:**
- `message` (dict): The message dictionary to send

**Returns:** The next message from the server (may be unsolicited)

---

#### `send_batch(messages: list[dict]) -> list[dict]`

Send multiple messages as a JSON array batch.

```python
responses = client.send_batch([
    {"message": "stats"},
    {"message": "config_get"},
])
# Output: [
#     {"message": "stats", "message_id": 1, ...},
#     {"message": "config_get", "message_id": 2, ...},
# ]
```

**Parameters:**
- `messages` (list[dict]): List of message dictionaries to send

**Returns:** List of response dictionaries, one per input message

---

#### `listen(callback: Callable, duration: float | None = None)`

Listen for unsolicited messages (events, logs, registered data).

```python
def handle_event(msg):
    print(f"Received: {msg}")
    if msg.get("message") == "ue_event":
        print(f"UE event: {msg.get('event')}")
    return True  # Continue listening (return False to stop)

# Listen for 30 seconds
client.listen(handle_event, duration=30.0)

# Listen indefinitely until callback returns False
client.listen(handle_event)
```

**Parameters:**
- `callback` (Callable): Called with each received message. Return `False` to stop listening.
- `duration` (float | None): Maximum listen time in seconds. `None` for indefinite.

---

### Context Manager Usage

```python
with WebSocketClient(host="192.168.1.80", port=9001) as client:
    response = client.send({"message": "stats"})
    print(response)
# Connection automatically closed
```

---

## HTTPOverSSHClient

HTTP client that forwards requests through an SSH tunnel. Same interface as `HTTPClient`.

### Import

```python
from client.http_ssh import HTTPOverSSHClient
```

### Constructor

```python
HTTPOverSSHClient(
    ssh_host: str,
    ssh_username: str,
    ssh_port: int = 22,
    ssh_password: str | None = None,
    ssh_key_path: str | None = None,
    remote_host: str = "localhost",
    remote_port: int = 9010,
    local_port: int = 19010,
    timeout: float = 30.0,
    retries: int = 3,
    api_key: str | None = None,
    connect_timeout: float = 10.0,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ssh_host` | `str` | *required* | Hostname or IP of the SSH server |
| `ssh_username` | `str` | *required* | SSH username |
| `ssh_port` | `int` | `22` | SSH port |
| `ssh_password` | `str \| None` | `None` | SSH password (requires `sshpass`) |
| `ssh_key_path` | `str \| None` | `None` | Path to SSH private key file |
| `remote_host` | `str` | `"localhost"` | Host where REST API is running on remote side |
| `remote_port` | `int` | `9010` | REST API port on remote side |
| `local_port` | `int` | `19010` | Local port for the tunnel |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `retries` | `int` | `3` | Number of retries for failed requests |
| `api_key` | `str \| None` | `None` | Optional API key for REST API |
| `connect_timeout` | `float` | `10.0` | SSH connection timeout in seconds |

### Properties

#### `connected -> bool`

Check if SSH tunnel is active.

```python
print(client.connected)
# Output: False (before connect)

client.connect()
print(client.connected)
# Output: True
```

#### `base_url -> str`

Get the local tunnel URL.

```python
client = HTTPOverSSHClient(ssh_host="192.168.1.80", ssh_username="root", local_port=19010)
print(client.base_url)
# Output: "http://localhost:19010"
```

### Methods

#### `is_listening(timeout: float = 2.0) -> bool`

Check if the SSH host is reachable.

```python
client = HTTPOverSSHClient(
    ssh_host="192.168.1.80",
    ssh_username="root",
)

if client.is_listening():
    print("SSH service is reachable")
    client.connect()
else:
    print("SSH service is not available")
```

**Note:** This checks SSH connectivity, not the REST API. Use `health_check()` after connecting to check the REST API.

**Parameters:**
- `timeout` (float): Connection timeout in seconds (default: 2.0)

**Returns:** `True` if SSH service is listening, `False` otherwise

---

#### `is_tunnel_active() -> bool`

Check if the SSH tunnel is active and forwarding traffic.

```python
if client.is_tunnel_active():
    response = client.get("/health")
```

**Returns:** `True` if tunnel is established and active, `False` otherwise

---

#### `connect()`

Establish SSH tunnel.

```python
# Using password authentication
client = HTTPOverSSHClient(
    ssh_host="192.168.1.80",
    ssh_username="root",
    ssh_password="amarisoft",
)
client.connect()

# Using key-based authentication
client = HTTPOverSSHClient(
    ssh_host="192.168.1.80",
    ssh_username="root",
    ssh_key_path="~/.ssh/id_rsa",
)
client.connect()

# Using IPv6
client = HTTPOverSSHClient(
    ssh_host="2620:10d:c052:12a:aaa1:59ff:fe88:d39",
    ssh_username="root",
    ssh_password="toor",
)
client.connect()
```

**Raises:**
- `SSHConnectionError`: If SSH connection fails
- `SSHTimeoutError`: If connection times out

---

#### `close()`

Close SSH tunnel.

```python
client.close()
```

---

#### `reconnect()`

Close and re-establish the SSH tunnel.

```python
client.reconnect()
```

---

#### HTTP Methods

Same interface as `HTTPClient`: `get()`, `post()`, `put()`, `delete()`, `health_check()`

```python
client.connect()

# GET request
response = client.get("/health")
response = client.get("/enb/stats", params={"rf": True})

# POST request
response = client.post("/enb/cells/1/activate")
response = client.post("/mme/ue/1/pdn", data={"apn": "internet", "pdn_type": "ipv4"})

# DELETE request
response = client.delete("/mme/ue/1/pdn/5")
```

---

### Context Manager Usage

```python
with HTTPOverSSHClient(
    ssh_host="192.168.1.80",
    ssh_username="root",
    ssh_password="amarisoft",
) as client:
    response = client.get("/health")
    print(response)
# Tunnel automatically closed
```

---

### Complete Example

```python
from client.http_ssh import HTTPOverSSHClient

# Configuration
SSH_HOST = "192.168.1.80"  # or IPv6 address
SSH_USER = "root"
SSH_PASS = "amarisoft"

client = HTTPOverSSHClient(
    ssh_host=SSH_HOST,
    ssh_username=SSH_USER,
    ssh_password=SSH_PASS,
    local_port=19010,
    remote_port=9010,
)

# Check if SSH is reachable first
if not client.is_listening():
    print("SSH service is not reachable")
    exit(1)

# Establish tunnel and make requests
with client:
    # Check API health
    health = client.health_check()
    print(f"API Status: {health}")
    
    # Get eNB stats
    stats = client.get("/enb/stats")
    print(f"eNB Stats: {stats}")

print("Done!")
```

---

## API Endpoints Reference

The REST API service provides endpoints organized by service type.

### System Endpoints

Base path: `/`

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| GET | `/health` | Health check with backend connectivity | - |
| GET | `/health/live` | Liveness probe (container orchestration) | - |
| GET | `/health/ready` | Readiness probe | - |
| GET | `/version` | Get API and service versions | - |
| GET | `/services` | Get all service connection status | - |
| GET | `/services/{service}` | Get single service status | `connect`: bool |
| POST | `/services/{service}/connect` | Connect to specific service | - |
| POST | `/services/{service}/disconnect` | Disconnect from specific service | - |
| POST | `/services/{service}/reconnect` | Reconnect to specific service | - |
| POST | `/services/connect` | Connect to all services | - |
| POST | `/services/disconnect` | Disconnect from all services | - |

#### Examples

```python
# Health check
response = client.get("/health")
# Output: {
#     "status": "healthy",
#     "timestamp": "2024-06-01T12:00:00Z",
#     "version": "1.0.0",
#     "callbox": {"host": "192.168.1.80", "connected_services": 4, "total_services": 4}
# }

# Get all service status
response = client.get("/services")
# Output: {
#     "host": "192.168.1.80",
#     "healthy": true,
#     "services": {
#         "enb": {"connected": true, "version": "2024-06-01"},
#         "mme": {"connected": true, "version": "2024-06-01"},
#         "ue": {"connected": true, "version": "2024-06-01"}
#     }
# }

# Connect to eNB
response = client.post("/services/enb/connect")
# Output: {"action": "connect", "service": {"connected": true, ...}}
```

---

### eNB/gNB Endpoints

Base path: `/enb`

#### System Information

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/enb/version` | Get eNB software version |
| GET | `/enb/help` | List available API commands |
| GET | `/enb/license` | Get license information |
| POST | `/enb/quit` | Terminate eNB process ⚠️ |

#### Statistics & Configuration

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| GET | `/enb/stats` | Get eNB statistics | `samples`: bool, `rf`: bool |
| GET | `/enb/config` | Get current configuration | - |
| POST | `/enb/config` | Set configuration | Body: `{"config": {...}}` |

#### UE Management

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| GET | `/enb/ue` | List connected UEs | `imsi`: str, `enb_ue_id`: int |
| GET | `/enb/ue/{enb_ue_id}` | Get UE by ID | - |
| POST | `/enb/ue/{enb_ue_id}/rrc-release` | Release RRC connection | Body: `{"cause": str, "redirect_freq": int}` |
| POST | `/enb/ue/{enb_ue_id}/handover` | Trigger handover | Body: `{"target_cell_id": int, "target_pci": int}` |

#### Cell Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/enb/cells` | List all cells |
| GET | `/enb/cells/{cell_id}` | Get cell by ID |
| POST | `/enb/cells/{cell_id}/gain` | Set cell gain/attenuation |
| POST | `/enb/cells/{cell_id}/activate` | Activate cell |
| POST | `/enb/cells/{cell_id}/deactivate` | Deactivate cell |
| POST | `/enb/cells/{cell_id}/mib-update` | Trigger MIB update |
| POST | `/enb/cells/{cell_id}/sib-update` | Trigger SIB update |

#### Paging & Logging

| Method | Endpoint | Description | Query Params / Body |
|--------|----------|-------------|---------------------|
| POST | `/enb/paging` | Send paging message | Body: `{"imsi": str, "domain": str}` |
| GET | `/enb/logs` | Get log entries | `min`: int, `max`: int, `layer`: str, `timeout`: float |
| POST | `/enb/logs/config` | Configure logging | Body: `{"layers": [...], "max_size": int}` |

#### Examples

```python
# Get eNB statistics with RF info
response = client.get("/enb/stats", params={"rf": True, "samples": True})
# Output: {
#     "message": "stats",
#     "cells": [{"cell_id": 1, "dl_bitrate": 150000000, ...}],
#     "ues": [{"enb_ue_id": 1, "imsi": "001010123456789", ...}]
# }

# List connected UEs
response = client.get("/enb/ue")
# Output: {"message": "ue_get", "ue_list": [...]}

# Activate a cell
response = client.post("/enb/cells/1/activate")
# Output: {"message": "cell_activate", "cell_id": 1}

# Set cell gain
response = client.post("/enb/cells/1/gain", data={"gain": -10})
# Output: {"message": "cell_gain", "cell_id": 1, "gain": -10}

# Trigger handover
response = client.post("/enb/ue/1/handover", data={
    "target_cell_id": 2,
    "target_pci": 100
})
# Output: {"message": "handover", "enb_ue_id": 1, "target_cell_id": 2}
```

---

### MME/AMF Endpoints

Base path: `/mme`

#### System Information

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mme/version` | Get MME software version |
| GET | `/mme/help` | List available API commands |
| POST | `/mme/quit` | Terminate MME process ⚠️ |

#### Statistics & Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mme/stats` | Get MME statistics |
| GET | `/mme/config` | Get current configuration |
| POST | `/mme/config` | Set configuration |

#### UE Management

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| GET | `/mme/ue` | List registered UEs | `imsi`: str, `mme_ue_id`: int |
| GET | `/mme/ue/{mme_ue_id}` | Get UE by MME ID | - |
| GET | `/mme/ue/imsi/{imsi}` | Get UE by IMSI | - |
| POST | `/mme/ue/{mme_ue_id}/release` | Release/detach UE | Body: `{"cause": str}` |
| POST | `/mme/ue/imsi/{imsi}/release` | Release UE by IMSI | Body: `{"cause": str}` |

#### PDN Connection Management

| Method | Endpoint | Description | Body |
|--------|----------|-------------|------|
| POST | `/mme/ue/{mme_ue_id}/pdn` | Create PDN connection | `{"apn": str, "pdn_type": str, "qci": int}` |
| DELETE | `/mme/ue/{mme_ue_id}/pdn/{pdn_id}` | Disconnect PDN | - |

#### Bearer Management

| Method | Endpoint | Description | Body |
|--------|----------|-------------|------|
| POST | `/mme/ue/{mme_ue_id}/bearer` | Create dedicated bearer | `{"qci": int, "gbr_dl": int, "gbr_ul": int, "mbr_dl": int, "mbr_ul": int, "arp_priority": int, "tft": {...}}` |
| DELETE | `/mme/ue/{mme_ue_id}/bearer/{bearer_id}` | Delete bearer | - |

#### SMS & Paging

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| POST | `/mme/ue/{mme_ue_id}/sms` | Send SMS to UE | `message`: str (required) |
| POST | `/mme/ue/imsi/{imsi}/sms` | Send SMS by IMSI | `message`: str (required) |
| POST | `/mme/paging` | Page a UE | `imsi`: str (required) |

#### APN & Logging

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mme/apn` | List configured APNs |
| GET | `/mme/logs` | Get log entries |
| POST | `/mme/logs/config` | Configure logging |

#### Examples

```python
# List registered UEs
response = client.get("/mme/ue")
# Output: {"message": "ue_get", "ue_list": [...]}

# Get UE by IMSI
response = client.get("/mme/ue/imsi/001010123456789")
# Output: {"message": "ue_get", "imsi": "001010123456789", "mme_ue_id": 1, ...}

# Create PDN connection
response = client.post("/mme/ue/1/pdn", data={
    "apn": "internet",
    "pdn_type": "ipv4",
    "qci": 9
})
# Output: {"message": "pdn_connect", "pdn_id": 5, "ip_addr": "10.45.0.2"}

# Create dedicated bearer
response = client.post("/mme/ue/1/bearer", data={
    "qci": 1,
    "gbr_dl": 128000,
    "gbr_ul": 64000
})
# Output: {"message": "bearer_activate", "bearer_id": 6}

# Send SMS
response = client.post("/mme/ue/1/sms", params={"message": "Hello from Amarisoft!"})
# Output: {"message": "sms_send"}

# Release UE
response = client.post("/mme/ue/1/release", data={"cause": "detach"})
# Output: {"message": "ue_release"}
```

---

### UE Simulator Endpoints

Base path: `/ue`

#### System Information

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ue/version` | Get UE Simulator version |
| GET | `/ue/help` | List available API commands |

#### Statistics & Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ue/stats` | Get UE Simulator statistics |
| GET | `/ue/config` | Get current configuration |
| POST | `/ue/config` | Set configuration |

#### UE Management

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| GET | `/ue/list` | List simulated UEs | `ue_id`: int, `imsi`: str |
| GET | `/ue/{ue_id}` | Get UE by ID | - |

#### Power Control

| Method | Endpoint | Description | Body |
|--------|----------|-------------|------|
| POST | `/ue/power/on` | Power on all UEs | `{"ue_id": int}` (optional) |
| POST | `/ue/power/off` | Power off all UEs | `{"ue_id": int}` (optional) |
| POST | `/ue/{ue_id}/power/on` | Power on specific UE | - |
| POST | `/ue/{ue_id}/power/off` | Power off specific UE | - |

#### Bearer & RRC

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| POST | `/ue/{ue_id}/bearer/dedicated` | Activate dedicated bearer | `def_bearer_id`: int, `qci`: int (1-9) |
| POST | `/ue/{ue_id}/rrc/assistance` | Send UE Assistance Info (5G NR) | `preferred_state`: str |

#### Logging

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ue/logs` | Get log entries |
| POST | `/ue/logs/config` | Configure logging |

#### Examples

```python
# List all simulated UEs
response = client.get("/ue/list")
# Output: {"message": "ue_get", "ue_list": [{"ue_id": 1, "imsi": "001010123456789", ...}]}

# Get specific UE
response = client.get("/ue/1")
# Output: {"message": "ue_get", "ue_id": 1, "state": "connected", ...}

# Power on all UEs
response = client.post("/ue/power/on")
# Output: {"message": "power_on"}

# Power off specific UE
response = client.post("/ue/2/power/off")
# Output: {"message": "power_off", "ue_id": 2}

# Activate dedicated bearer
response = client.post("/ue/1/bearer/dedicated", params={
    "def_bearer_id": 5,
    "qci": 1
})
# Output: {"message": "ue_activate_dedicated_bearer"}

# Send UE Assistance Information (5G NR)
response = client.post("/ue/1/rrc/assistance", params={
    "preferred_state": "inactive"
})
# Output: {"message": "ue_assistance_information"}
```

---

## Error Handling

### HTTP Client Exceptions

```python
from client.http.exceptions import (
    HTTPClientError,      # Base exception
    ConnectionError,      # Connection failed
    TimeoutError,         # Request timed out
    APIError,             # API returned error (4xx/5xx)
    AuthenticationError,  # Authentication failed (401)
)

try:
    response = client.get("/endpoint")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except TimeoutError as e:
    print(f"Request timed out: {e}")
except APIError as e:
    print(f"API error: {e.message} (HTTP {e.status_code})")
except AuthenticationError as e:
    print(f"Auth failed: {e}")
```

### WebSocket Client Exceptions

```python
from client.websocket.exceptions import (
    AmariError,           # Base exception
    AmariConnectionError, # Connection failed
    AmariTimeoutError,    # Request timed out
    CommandError,         # Server returned error
    AuthenticationError,  # Authentication failed
)

try:
    response = client.send({"message": "stats"})
except AmariConnectionError as e:
    print(f"Connection failed: {e}")
except CommandError as e:
    print(f"Command error: {e} (code: {e.error_code})")
except AmariTimeoutError as e:
    print(f"Timeout: {e}")
```

### SSH Client Exceptions

```python
from client.http_ssh.exceptions import (
    SSHClientError,       # Base exception
    SSHConnectionError,   # SSH connection failed
    SSHTimeoutError,      # SSH connection timed out
    SSHTunnelError,       # Tunnel creation failed
    APIError,             # API returned error
    AuthenticationError,  # Auth failed
)

try:
    client.connect()
    response = client.get("/health")
except SSHConnectionError as e:
    print(f"SSH connection failed: {e}")
except SSHTimeoutError as e:
    print(f"SSH timed out: {e}")
except APIError as e:
    print(f"API error: {e}")
```

---

## Best Practices

### 1. Always Check Connectivity First

```python
if client.is_listening():
    client.connect()
    # ... use client
else:
    print("Service not available")
```

### 2. Use Context Managers

```python
# Ensures proper cleanup
with HTTPClient("http://192.168.1.80:9010") as client:
    response = client.get("/health")
```

### 3. Handle Errors Gracefully

```python
try:
    with HTTPOverSSHClient(...) as client:
        response = client.get("/health")
except SSHConnectionError:
    print("Could not establish SSH tunnel")
except APIError as e:
    print(f"API error: {e}")
```

### 4. Use Appropriate Timeouts

```python
# Longer timeout for slow networks
client = HTTPClient("http://192.168.1.80:9010", timeout=60.0)

# Quick connectivity check
if client.is_listening(timeout=1.0):
    # ...
```

### 5. Reuse Clients

```python
# Good: Reuse client for multiple requests
client = HTTPClient("http://192.168.1.80:9010")
for i in range(100):
    client.get("/stats")
client.close()

# Bad: Create new client for each request
for i in range(100):
    client = HTTPClient("http://192.168.1.80:9010")
    client.get("/stats")
    client.close()
```

---

## Quick Reference

### Client Methods

| Method | HTTPClient | WebSocketClient | HTTPOverSSHClient |
|--------|------------|-----------------|-------------------|
| `is_listening()` | ✅ | ✅ | ✅ |
| `connect()` | - | ✅ | ✅ |
| `reconnect()` | - | ✅ | ✅ |
| `close()` | ✅ | ✅ | ✅ |
| `get()` | ✅ | - | ✅ |
| `post()` | ✅ | - | ✅ |
| `put()` | ✅ | - | ✅ |
| `delete()` | ✅ | - | ✅ |
| `health_check()` | ✅ | - | ✅ |
| `send()` | - | ✅ | - |
| `send_batch()` | - | ✅ | - |
| `listen()` | - | ✅ | - |
| `is_tunnel_active()` | - | - | ✅ |

### Endpoint Summary

| Service | Prefix | Key Endpoints |
|---------|--------|---------------|
| System | `/` | `/health`, `/services`, `/version` |
| eNB/gNB | `/enb` | `/stats`, `/ue`, `/cells`, `/config` |
| MME/AMF | `/mme` | `/stats`, `/ue`, `/pdn`, `/bearer`, `/sms` |
| UE Simulator | `/ue` | `/list`, `/power/on`, `/power/off`, `/stats` |
