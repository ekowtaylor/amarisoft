"""IMS (IP Multimedia Subsystem) Remote API methods."""

from __future__ import annotations

from typing import Any

from .base import ServiceApi


class IMSApi(ServiceApi):
    """API for controlling an Amarisoft IMS server via the Remote API.

    Provides methods for user management, call control, SMS/MMS,
    dialog management, and event subscription.

    Inherits common methods from :class:`ServiceApi`:
    ``config_get``, ``config_set``, ``stats``, ``ue_get``,
    ``log_get``, ``log_set``, ``version``, ``help``.

    Remote API Commands Summary:
        - User Management: users_get, users_add, user_set, unregister
        - IMPU Management: impu_set, impu_add, impu_del
        - Call Control: mt_call, call_release, call_transfer, conference
        - Dialog Management: dialog_get, dialog_set
        - SMS/MMS: send_sms, sms_flush, send_mms, mms_server
        - Media: media_inject, media_stream
        - Supplementary Services: supplementary_service
        - Emergency: emergency_call
        - Registration: register_events, registration_status
        - Utility: cancel, echo, license, monitor, quit
    """

    DEFAULT_PORT = 9002

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
        msg: dict[str, Any] = {"message": "users_get"}
        if registered_only:
            msg["registered_only"] = True
        return self._client.send(msg)

    def users_add(self, **params: Any) -> dict[str, Any]:
        """Add users to the IMS database.

        Args:
            **params: User configuration parameters.
        """
        msg: dict[str, Any] = {"message": "users_add"}
        msg.update(params)
        return self._client.send(msg)

    def user_set(self, **params: Any) -> dict[str, Any]:
        """Configure an existing IMS user.

        Args:
            **params: User parameters to set.
        """
        msg: dict[str, Any] = {"message": "user_set"}
        msg.update(params)
        return self._client.send(msg)

    def unregister(self, impu: str) -> dict[str, Any]:
        """Force network deregistration of a user.

        Args:
            impu: IMS Public User Identity to deregister.
        """
        return self._client.send({
            "message": "unregister",
            "impu": impu,
        })

    # ──────────────────────────────────────────────
    # IMPU Management
    # ──────────────────────────────────────────────

    def impu_set(self, impu: str, **params: Any) -> dict[str, Any]:
        """Configure an IMS Public User Identity (IMPU).

        Args:
            impu: The IMPU to configure.
            **params: IMPU parameters.
        """
        msg: dict[str, Any] = {"message": "impu_set", "impu": impu}
        msg.update(params)
        return self._client.send(msg)

    def impu_add(self, impu: str, **params: Any) -> dict[str, Any]:
        """Add an IMPU to a user.

        Args:
            impu: The IMPU to add.
            **params: Additional parameters.
        """
        msg: dict[str, Any] = {"message": "impu_add", "impu": impu}
        msg.update(params)
        return self._client.send(msg)

    def impu_del(self, impu: str) -> dict[str, Any]:
        """Remove an IMPU from a user.

        Args:
            impu: The IMPU to remove.
        """
        return self._client.send({
            "message": "impu_del",
            "impu": impu,
        })

    # ──────────────────────────────────────────────
    # Paging
    # ──────────────────────────────────────────────

    def mt_cs_paging(self, imsi: str) -> dict[str, Any]:
        """Initiate circuit-switched mobile-terminated paging via IMS.

        Args:
            imsi: IMSI of the target UE.
        """
        return self._client.send({
            "message": "mt_cs_paging",
            "imsi": imsi,
        })

    # ──────────────────────────────────────────────
    # Call Control
    # ──────────────────────────────────────────────

    def mt_call(self, impu: str, **params: Any) -> dict[str, Any]:
        """Initiate a mobile-terminated call.

        Args:
            impu: IMS Public User Identity to call.
            **params: Additional call parameters.
        """
        msg: dict[str, Any] = {"message": "mt_call", "impu": impu}
        msg.update(params)
        return self._client.send(msg)

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
        msg: dict[str, Any] = {"message": "dialog_get"}
        if session_id is not None:
            msg["session_id"] = session_id
        return self._client.send(msg)

    def dialog_set(
        self,
        session_id: str,
        action: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Perform an action on an active dialog.

        Args:
            session_id: Target dialog session ID.
            action: Action to perform (``"stop"``, ``"answer"``,
                ``"reinvite"``, ``"hold"``, ``"downgrade"``).
            **params: Additional action parameters.
        """
        msg: dict[str, Any] = {
            "message": "dialog_set",
            "session_id": session_id,
            "action": action,
        }
        msg.update(params)
        return self._client.send(msg)

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
            impu: IMS Public User Identity (e.g., ``"sip:user@domain"``).
            text: Plain text message content.
            binary_hex: Binary message payload as hex string
                (alternative to *text*).
        """
        msg: dict[str, Any] = {
            "message": "sms",
            "impu": impu,
        }
        if binary_hex is not None:
            msg["binary_hex"] = binary_hex
        elif text is not None:
            msg["text"] = text
        return self._client.send(msg)

    def sms_flush(self) -> dict[str, Any]:
        """Flush all pending SMS messages."""
        return self._client.send({"message": "sms_flush"})

    # ──────────────────────────────────────────────
    # MMS
    # ──────────────────────────────────────────────

    def send_mms(self, impu: str, filename: str, **params: Any) -> dict[str, Any]:
        """Send an MMS message to a UE.

        Args:
            impu: IMS Public User Identity.
            filename: Path to the file to send (jpg, png, gif, txt).
            **params: Additional MMS parameters.
        """
        msg: dict[str, Any] = {
            "message": "mms",
            "impu": impu,
            "filename": filename,
        }
        msg.update(params)
        return self._client.send(msg)

    def mms_server(self) -> dict[str, Any]:
        """Retrieve the MMS server address."""
        return self._client.send({"message": "mms_server"})

    # ──────────────────────────────────────────────
    # License & Security
    # ──────────────────────────────────────────────

    def license(self) -> dict[str, Any]:
        """Retrieve license information.

        Returns:
            License details including products, user, validity,
            and server info.
        """
        return self._client.send({"message": "license"})

    def ipsec(self) -> dict[str, Any]:
        """Retrieve IPsec security association details.

        Returns:
            IPsec SA info with type, direction, SPI, and
            encryption details.
        """
        return self._client.send({"message": "ipsec"})

    # ──────────────────────────────────────────────
    # Event Registration
    # ──────────────────────────────────────────────

    def register_events(self, *event_types: str) -> dict[str, Any]:
        """Register to receive specific event types.

        Args:
            *event_types: Event types to subscribe to (e.g.,
                ``"users_update"``, ``"sms"``, ``"dialog"``).
        """
        return self._client.send({
            "message": "register",
            "register": list(event_types),
        })

    # ──────────────────────────────────────────────
    # Call Control (Extended)
    # ──────────────────────────────────────────────

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
            Response from the IMS.
        """
        msg: dict[str, Any] = {
            "message": "call_release",
            "session_id": session_id,
        }
        if cause is not None:
            msg["cause"] = cause
        return self._client.send(msg)

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
            Response from the IMS.
        """
        return self._client.send({
            "message": "call_transfer",
            "session_id": session_id,
            "target_impu": target_impu,
            "transfer_type": transfer_type,
        })

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
            Response from the IMS.
        """
        return self._client.send({
            "message": "conference",
            "session_ids": session_ids,
            "action": action,
        })

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
            Response from the IMS.
        """
        msg: dict[str, Any] = {
            "message": "emergency_call",
            "impu": impu,
            "emergency_type": emergency_type,
        }
        msg.update(params)
        return self._client.send(msg)

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
            Response from the IMS.
        """
        msg: dict[str, Any] = {
            "message": "media_inject",
            "session_id": session_id,
            "media_type": media_type,
            "payload": payload,
        }
        msg.update(params)
        return self._client.send(msg)

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
            Response from the IMS.
        """
        msg: dict[str, Any] = {
            "message": "media_stream",
            "session_id": session_id,
            "action": action,
        }
        msg.update(params)
        return self._client.send(msg)

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
            Response from the IMS.
        """
        msg: dict[str, Any] = {
            "message": "supplementary_service",
            "impu": impu,
            "service": service,
            "action": action,
        }
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Registration Status
    # ──────────────────────────────────────────────

    def registration_status(
        self,
        impu: str | None = None,
    ) -> dict[str, Any]:
        """Get registration status.

        Args:
            impu: Optional IMPU to query.

        Returns:
            Registration status information.
        """
        msg: dict[str, Any] = {"message": "registration_status"}
        if impu is not None:
            msg["impu"] = impu
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Utility Commands
    # ──────────────────────────────────────────────

    def cancel(self, request_id: int) -> dict[str, Any]:
        """Cancel a pending async request.

        Args:
            request_id: ID of the request to cancel.

        Returns:
            Cancel result.
        """
        return self._client.send({
            "message": "cancel",
            "request_id": request_id,
        })

    def echo(self, data: Any = None) -> dict[str, Any]:
        """Echo test - returns the sent data.

        Args:
            data: Optional data to echo back.

        Returns:
            Echo response with the sent data.
        """
        msg: dict[str, Any] = {"message": "echo"}
        if data is not None:
            msg["data"] = data
        return self._client.send(msg)

    def monitor(
        self,
        enable: bool = True,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Enable or disable event monitoring.

        Args:
            enable: True to enable monitoring, False to disable.
            events: Optional list of event types to monitor.

        Returns:
            Monitor configuration result.
        """
        msg: dict[str, Any] = {
            "message": "monitor",
            "enable": enable,
        }
        if events is not None:
            msg["events"] = events
        return self._client.send(msg)

    def quit(self) -> dict[str, Any]:
        """Quit the IMS service.

        Returns:
            Quit acknowledgment.
        """
        return self._client.send({"message": "quit"})

    # ──────────────────────────────────────────────
    # Logging (Extended)
    # ──────────────────────────────────────────────

    def log_bin_get(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        max_count: int | None = None,
    ) -> dict[str, Any]:
        """Get binary log entries.

        Args:
            start_time: Start timestamp.
            end_time: End timestamp.
            max_count: Maximum number of entries.

        Returns:
            Binary log entries.
        """
        msg: dict[str, Any] = {"message": "log_bin_get"}
        if start_time is not None:
            msg["start_time"] = start_time
        if end_time is not None:
            msg["end_time"] = end_time
        if max_count is not None:
            msg["max_count"] = max_count
        return self._client.send(msg)

    def log_reset(self) -> dict[str, Any]:
        """Reset the log buffer.

        Returns:
            Reset confirmation.
        """
        return self._client.send({"message": "log_reset"})
