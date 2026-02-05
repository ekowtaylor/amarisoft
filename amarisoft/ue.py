"""UE Simulator Remote API methods."""

from __future__ import annotations

from typing import Any

from .base import ServiceApi


class UEApi(ServiceApi):
    """API for controlling an Amarisoft UE Simulator via the Remote API.

    Provides methods for managing simulated UEs, controlling their state,
    and performing test procedures.

    Inherits common methods from :class:`ServiceApi`:
    ``config_get``, ``config_set``, ``stats``, ``ue_get``,
    ``log_get``, ``log_set``.
    """

    DEFAULT_PORT = 9003

    # ──────────────────────────────────────────────
    # UE Power Control
    # ──────────────────────────────────────────────

    def power_on(self, ue_id: int | None = None) -> dict[str, Any]:
        """Power on a simulated UE.

        Args:
            ue_id: Specific UE to power on. ``None`` for all UEs.
        """
        msg: dict[str, Any] = {"message": "power_on"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        return self._client.send(msg)

    def power_off(self, ue_id: int | None = None) -> dict[str, Any]:
        """Power off a simulated UE.

        Args:
            ue_id: Specific UE to power off. ``None`` for all UEs.
        """
        msg: dict[str, Any] = {"message": "power_off"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Bearer Management
    # ──────────────────────────────────────────────

    def ue_activate_dedicated_bearer(
        self,
        ue_id: int,
        def_bearer_id: int,
        qci: int,
        gbr: dict[str, Any] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Activate a dedicated bearer for a simulated UE.

        Args:
            ue_id: Target UE identifier.
            def_bearer_id: Default bearer ID to associate with.
            qci: QoS Class Identifier.
            gbr: Guaranteed bit rate configuration with keys like
                ``"dl_gbr"``, ``"ul_gbr"``, ``"dl_mbr"``, ``"ul_mbr"``.
            filters: Traffic flow template filters, each containing
                ``"direction"``, ``"id"``, ``"precedence"``, ``"components"``.
        """
        msg: dict[str, Any] = {
            "message": "ue_activate_dedicated_bearer",
            "ue_id": ue_id,
            "def_bearer_id": def_bearer_id,
            "qci": qci,
        }
        if gbr is not None:
            msg["gbr"] = gbr
        if filters is not None:
            msg["filters"] = filters
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # UE Assistance Information (NR)
    # ──────────────────────────────────────────────

    def ue_assistance_information(
        self,
        ue_id: int,
        preferred_rrc_state: str | None = None,
    ) -> dict[str, Any]:
        """Send UE Assistance Information (5G NR).

        Args:
            ue_id: Target UE identifier.
            preferred_rrc_state: Preferred RRC state
                (``"connected"``, ``"inactive"``, ``"idle"``).
        """
        msg: dict[str, Any] = {
            "message": "ue_assistance_information",
            "ue_id": ue_id,
        }
        if preferred_rrc_state is not None:
            msg["preferred_rrc_state"] = preferred_rrc_state
        return self._client.send(msg)
