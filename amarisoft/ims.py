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
