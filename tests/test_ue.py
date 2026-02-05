"""Tests for UEApi-specific methods."""

from __future__ import annotations


class TestPowerOn:
    def test_all(self, mock_client, ue):
        ue.power_on()
        mock_client.send.assert_called_once_with({"message": "power_on"})

    def test_specific_ue(self, mock_client, ue):
        ue.power_on(ue_id=1)
        mock_client.send.assert_called_once_with(
            {"message": "power_on", "ue_id": 1}
        )


class TestPowerOff:
    def test_all(self, mock_client, ue):
        ue.power_off()
        mock_client.send.assert_called_once_with({"message": "power_off"})

    def test_specific_ue(self, mock_client, ue):
        ue.power_off(ue_id=2)
        mock_client.send.assert_called_once_with(
            {"message": "power_off", "ue_id": 2}
        )


class TestUeActivateDedicatedBearer:
    def test_minimal(self, mock_client, ue):
        ue.ue_activate_dedicated_bearer(ue_id=1, def_bearer_id=5, qci=9)
        mock_client.send.assert_called_once_with({
            "message": "ue_activate_dedicated_bearer",
            "ue_id": 1,
            "def_bearer_id": 5,
            "qci": 9,
        })

    def test_with_gbr(self, mock_client, ue):
        gbr = {"dl_gbr": 128, "ul_gbr": 64}
        ue.ue_activate_dedicated_bearer(ue_id=1, def_bearer_id=5, qci=1, gbr=gbr)
        mock_client.send.assert_called_once_with({
            "message": "ue_activate_dedicated_bearer",
            "ue_id": 1,
            "def_bearer_id": 5,
            "qci": 1,
            "gbr": {"dl_gbr": 128, "ul_gbr": 64},
        })

    def test_with_filters(self, mock_client, ue):
        filters = [{"direction": "dl", "id": 1, "precedence": 10, "components": []}]
        ue.ue_activate_dedicated_bearer(
            ue_id=1, def_bearer_id=5, qci=5, filters=filters,
        )
        mock_client.send.assert_called_once_with({
            "message": "ue_activate_dedicated_bearer",
            "ue_id": 1,
            "def_bearer_id": 5,
            "qci": 5,
            "filters": filters,
        })


class TestUeAssistanceInformation:
    def test_without_preferred_rrc_state(self, mock_client, ue):
        ue.ue_assistance_information(ue_id=1)
        mock_client.send.assert_called_once_with({
            "message": "ue_assistance_information",
            "ue_id": 1,
        })

    def test_with_preferred_rrc_state(self, mock_client, ue):
        ue.ue_assistance_information(ue_id=1, preferred_rrc_state="idle")
        mock_client.send.assert_called_once_with({
            "message": "ue_assistance_information",
            "ue_id": 1,
            "preferred_rrc_state": "idle",
        })
