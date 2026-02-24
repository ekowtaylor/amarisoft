"""IMS (IP Multimedia Subsystem) HTTP API client."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import HTTPClient


class IMSApi:
    """HTTP client for IMS (IP Multimedia Subsystem) operations.

    Provides the same interface as the WebSocket IMSApi but uses HTTP.

    Example::

        from client.http import Callbox

        cb = Callbox("http://192.168.1.80:9010")
        users = cb.ims.users_get()
        cb.ims.send_sms(impu="sip:user@domain", text="Hello!")
    """

    def __init__(self, client: "HTTPClient"):
        self._client = client

    def version(self) -> dict[str, Any]:
        """Get IMS version information."""
        return self._client.get("/ims/version")

    def help(self) -> dict[str, Any]:
        """Get list of available API commands."""
        return self._client.get("/ims/help")

    def stats(self) -> dict[str, Any]:
        """Get IMS statistics.

        Returns:
            Statistics data including user counts and session metrics.
        """
        return self._client.get("/ims/stats")

    def config_get(self) -> dict[str, Any]:
        """Get IMS configuration."""
        return self._client.get("/ims/config")

    def config_set(self, **kwargs: Any) -> dict[str, Any]:
        """Set IMS configuration parameters.

        Args:
            **kwargs: Configuration parameters to set.

        Returns:
            Response from the API.
        """
        return self._client.post("/ims/config", data={"config": kwargs})

    # ──────────────────────────────────────────────
    # User Management
    # ──────────────────────────────────────────────

    def users_get(self, registered_only: bool = False) -> dict[str, Any]:
        """Query IMS users.

        Args:
            registered_only: If True, return only currently registered users.

        Returns:
            User list with bindings and dialog info.
        """
        params = {}
        if registered_only:
            params["registered_only"] = "true"
        return self._client.get("/ims/users", params=params if params else None)

    def users_add(self, **params: Any) -> dict[str, Any]:
        """Add users to the IMS database.

        Args:
            **params: User configuration parameters.

        Returns:
            Response from the API.
        """
        return self._client.post("/ims/users", data=params)

    def user_set(self, impu: str, **params: Any) -> dict[str, Any]:
        """Configure an existing IMS user.

        Args:
            impu: IMS Public User Identity.
            **params: User parameters to set.

        Returns:
            Response from the API.
        """
        data = {"impu": impu}
        data.update(params)
        return self._client.put("/ims/users", data=data)

    def unregister(self, impu: str) -> dict[str, Any]:
        """Force network deregistration of a user.

        Args:
            impu: IMS Public User Identity to deregister.

        Returns:
            Response from the API.
        """
        return self._client.post("/ims/unregister", data={"impu": impu})

    # ──────────────────────────────────────────────
    # IMPU Management
    # ──────────────────────────────────────────────

    def impu_set(self, impu: str, **params: Any) -> dict[str, Any]:
        """Configure an IMS Public User Identity (IMPU).

        Args:
            impu: The IMPU to configure.
            **params: IMPU parameters.

        Returns:
            Response from the API.
        """
        data = {"impu": impu}
        data.update(params)
        return self._client.post("/ims/impu/set", data=data)

    def impu_add(self, impu: str, **params: Any) -> dict[str, Any]:
        """Add an IMPU to a user.

        Args:
            impu: The IMPU to add.
            **params: Additional parameters.

        Returns:
            Response from the API.
        """
        data = {"impu": impu}
        data.update(params)
        return self._client.post("/ims/impu/add", data=data)

    def impu_del(self, impu: str) -> dict[str, Any]:
        """Remove an IMPU from a user.

        Args:
            impu: The IMPU to remove.

        Returns:
            Response from the API.
        """
        return self._client.delete(f"/ims/impu/{impu}")

    # ──────────────────────────────────────────────
    # Call Control
    # ──────────────────────────────────────────────

    def mt_call(self, impu: str, **params: Any) -> dict[str, Any]:
        """Initiate a mobile-terminated call.

        Args:
            impu: IMS Public User Identity to call.
            **params: Additional call parameters.

        Returns:
            Response from the API.
        """
        data = {"impu": impu}
        data.update(params)
        return self._client.post("/ims/call", data=data)

    def call_release(
        self,
        session_id: str,
        cause: int | None = None,
    ) -> dict[str, Any]:
        """Release/terminate an active call.

        Args:
            session_id: Target dialog session ID.
            cause: Optional release cause code.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"session_id": session_id}
        if cause is not None:
            data["cause"] = cause
        return self._client.post("/ims/call/release", data=data)

    def call_transfer(
        self,
        session_id: str,
        target_impu: str,
        transfer_type: str = "blind",
    ) -> dict[str, Any]:
        """Transfer an active call to another user.

        Args:
            session_id: Target dialog session ID.
            target_impu: IMPU to transfer the call to.
            transfer_type: "blind" or "attended".

        Returns:
            Response from the API.
        """
        return self._client.post(
            "/ims/call/transfer",
            data={
                "session_id": session_id,
                "target_impu": target_impu,
                "transfer_type": transfer_type,
            },
        )

    def conference(
        self,
        session_ids: list[str],
        action: str = "create",
    ) -> dict[str, Any]:
        """Create or modify a conference call.

        Args:
            session_ids: List of session IDs to include in conference.
            action: "create", "add", "remove".

        Returns:
            Response from the API.
        """
        return self._client.post(
            "/ims/conference",
            data={"session_ids": session_ids, "action": action},
        )

    def emergency_call(
        self,
        impu: str,
        emergency_type: str = "general",
        **params: Any,
    ) -> dict[str, Any]:
        """Initiate an emergency call.

        Args:
            impu: IMS Public User Identity making the call.
            emergency_type: Type of emergency ("general", "ambulance", "fire", "police").
            **params: Additional call parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"impu": impu, "emergency_type": emergency_type}
        data.update(params)
        return self._client.post("/ims/call/emergency", data=data)

    # ──────────────────────────────────────────────
    # Dialog Management
    # ──────────────────────────────────────────────

    def dialog_get(self, session_id: str | None = None) -> dict[str, Any]:
        """List current pending dialogs.

        Args:
            session_id: Optional session ID to filter by.

        Returns:
            Dialog list with state and media details.
        """
        params = {}
        if session_id:
            params["session_id"] = session_id
        return self._client.get("/ims/dialogs", params=params if params else None)

    def dialog_set(
        self,
        session_id: str,
        action: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Perform an action on an active dialog.

        Args:
            session_id: Target dialog session ID.
            action: Action to perform ("stop", "answer", "reinvite", "hold", "downgrade").
            **params: Additional action parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"session_id": session_id, "action": action}
        data.update(params)
        return self._client.post("/ims/dialogs/action", data=data)

    # ──────────────────────────────────────────────
    # SMS
    # ──────────────────────────────────────────────

    def send_sms(
        self,
        impu: str,
        text: str | None = None,
        binary_hex: str | None = None,
    ) -> dict[str, Any]:
        """Send an SMS message to a UE.

        Args:
            impu: IMS Public User Identity (e.g., "sip:user@domain").
            text: Plain text message content.
            binary_hex: Binary message payload as hex string (alternative to text).

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"impu": impu}
        if binary_hex is not None:
            data["binary_hex"] = binary_hex
        elif text is not None:
            data["text"] = text
        return self._client.post("/ims/sms", data=data)

    def sms_flush(self) -> dict[str, Any]:
        """Flush all pending SMS messages.

        Returns:
            Response from the API.
        """
        return self._client.post("/ims/sms/flush")

    # ──────────────────────────────────────────────
    # MMS
    # ──────────────────────────────────────────────

    def send_mms(self, impu: str, filename: str, **params: Any) -> dict[str, Any]:
        """Send an MMS message to a UE.

        Args:
            impu: IMS Public User Identity.
            filename: Path to the file to send (jpg, png, gif, txt).
            **params: Additional MMS parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"impu": impu, "filename": filename}
        data.update(params)
        return self._client.post("/ims/mms", data=data)

    def mms_server(self) -> dict[str, Any]:
        """Retrieve the MMS server address.

        Returns:
            MMS server information.
        """
        return self._client.get("/ims/mms/server")

    # ──────────────────────────────────────────────
    # Media Control
    # ──────────────────────────────────────────────

    def media_inject(
        self,
        session_id: str,
        media_type: str,
        payload: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Inject media into an active dialog.

        Args:
            session_id: Target dialog session ID.
            media_type: Type of media ("audio", "video").
            payload: Media payload (base64 or hex encoded).
            **params: Additional media parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {
            "session_id": session_id,
            "media_type": media_type,
            "payload": payload,
        }
        data.update(params)
        return self._client.post("/ims/media/inject", data=data)

    def media_stream(
        self,
        session_id: str,
        action: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Control media streaming for a dialog.

        Args:
            session_id: Target dialog session ID.
            action: "start", "stop", "mute", "unmute".
            **params: Additional stream parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"session_id": session_id, "action": action}
        data.update(params)
        return self._client.post("/ims/media/stream", data=data)

    # ──────────────────────────────────────────────
    # Supplementary Services
    # ──────────────────────────────────────────────

    def supplementary_service(
        self,
        impu: str,
        service: str,
        action: str = "activate",
        **params: Any,
    ) -> dict[str, Any]:
        """Manage supplementary services for a user.

        Args:
            impu: IMS Public User Identity.
            service: Service type ("call_forwarding", "call_barring",
                "call_waiting", "caller_id").
            action: "activate", "deactivate", "query".
            **params: Additional service parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"impu": impu, "service": service, "action": action}
        data.update(params)
        return self._client.post("/ims/supplementary", data=data)

    # ──────────────────────────────────────────────
    # Registration & Monitoring
    # ──────────────────────────────────────────────

    def registration_status(self, impu: str | None = None) -> dict[str, Any]:
        """Get registration status.

        Args:
            impu: Optional IMPU to query.

        Returns:
            Registration status information.
        """
        params = {}
        if impu:
            params["impu"] = impu
        return self._client.get("/ims/registration", params=params if params else None)

    # ──────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────

    def log_get(
        self,
        min_: int | None = None,
        max_: int | None = None,
        layer: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Get log entries.

        Args:
            min_: Minimum log index.
            max_: Maximum log index.
            layer: Filter by layer.
            timeout: Query timeout in seconds.

        Returns:
            Log entries.
        """
        params = {}
        if min_ is not None:
            params["min"] = min_
        if max_ is not None:
            params["max"] = max_
        if layer:
            params["layer"] = layer
        if timeout is not None:
            params["timeout"] = timeout
        return self._client.get("/ims/logs", params=params if params else None)

    def log_set(
        self,
        layers: dict[str, Any] | None = None,
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Configure logging.

        Args:
            layers: Per-layer log settings.
            max_size: Maximum log buffer size.

        Returns:
            Response from the API.
        """
        data = {}
        if layers:
            data["layers"] = layers
        if max_size:
            data["max_size"] = max_size
        return self._client.post("/ims/logs/config", data=data)

    def license(self) -> dict[str, Any]:
        """Get license information."""
        return self._client.get("/ims/license")

    def ipsec(self) -> dict[str, Any]:
        """Retrieve IPsec security association details."""
        return self._client.get("/ims/ipsec")

    def quit(self) -> dict[str, Any]:
        """Terminate the IMS process. Use with caution!"""
        return self._client.post("/ims/quit")
