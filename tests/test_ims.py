"""Tests for IMSApi-specific methods."""

from __future__ import annotations


class TestUsersGet:
    def test_default(self, mock_client, ims):
        ims.users_get()
        mock_client.send.assert_called_once_with({"message": "users_get"})

    def test_registered_only(self, mock_client, ims):
        ims.users_get(registered_only=True)
        mock_client.send.assert_called_once_with(
            {"message": "users_get", "registered_only": True}
        )


class TestUsersAdd:
    def test_sends(self, mock_client, ims):
        ims.users_add(imsi="001", impu="sip:user@domain")
        mock_client.send.assert_called_once_with({
            "message": "users_add",
            "imsi": "001",
            "impu": "sip:user@domain",
        })


class TestUserSet:
    def test_sends(self, mock_client, ims):
        ims.user_set(imsi="001", display_name="Test")
        mock_client.send.assert_called_once_with({
            "message": "user_set",
            "imsi": "001",
            "display_name": "Test",
        })


class TestUnregister:
    def test_sends(self, mock_client, ims):
        ims.unregister(impu="sip:user@domain")
        mock_client.send.assert_called_once_with({
            "message": "unregister",
            "impu": "sip:user@domain",
        })


class TestImpuSet:
    def test_sends(self, mock_client, ims):
        ims.impu_set("sip:user@domain", display_name="Test")
        mock_client.send.assert_called_once_with({
            "message": "impu_set",
            "impu": "sip:user@domain",
            "display_name": "Test",
        })


class TestImpuAdd:
    def test_sends(self, mock_client, ims):
        ims.impu_add("sip:user@domain", type="pub")
        mock_client.send.assert_called_once_with({
            "message": "impu_add",
            "impu": "sip:user@domain",
            "type": "pub",
        })


class TestImpuDel:
    def test_sends(self, mock_client, ims):
        ims.impu_del("sip:user@domain")
        mock_client.send.assert_called_once_with({
            "message": "impu_del",
            "impu": "sip:user@domain",
        })


class TestMtCsPaging:
    def test_sends(self, mock_client, ims):
        ims.mt_cs_paging(imsi="001")
        mock_client.send.assert_called_once_with({
            "message": "mt_cs_paging",
            "imsi": "001",
        })


class TestMtCall:
    def test_sends(self, mock_client, ims):
        ims.mt_call(impu="sip:user@domain", codec="amr")
        mock_client.send.assert_called_once_with({
            "message": "mt_call",
            "impu": "sip:user@domain",
            "codec": "amr",
        })


class TestDialogGet:
    def test_default(self, mock_client, ims):
        ims.dialog_get()
        mock_client.send.assert_called_once_with({"message": "dialog_get"})

    def test_with_session_id(self, mock_client, ims):
        ims.dialog_get(session_id="abc123")
        mock_client.send.assert_called_once_with({
            "message": "dialog_get",
            "session_id": "abc123",
        })


class TestDialogSet:
    def test_sends(self, mock_client, ims):
        ims.dialog_set("abc123", "answer")
        mock_client.send.assert_called_once_with({
            "message": "dialog_set",
            "session_id": "abc123",
            "action": "answer",
        })

    def test_with_extra_params(self, mock_client, ims):
        ims.dialog_set("abc123", "reinvite", codec="amr")
        mock_client.send.assert_called_once_with({
            "message": "dialog_set",
            "session_id": "abc123",
            "action": "reinvite",
            "codec": "amr",
        })


class TestSendSms:
    def test_with_text(self, mock_client, ims):
        ims.send_sms(impu="sip:user@domain", text="hello")
        mock_client.send.assert_called_once_with({
            "message": "sms",
            "impu": "sip:user@domain",
            "text": "hello",
        })

    def test_with_binary_hex(self, mock_client, ims):
        ims.send_sms(impu="sip:user@domain", binary_hex="DEADBEEF")
        mock_client.send.assert_called_once_with({
            "message": "sms",
            "impu": "sip:user@domain",
            "binary_hex": "DEADBEEF",
        })

    def test_without_content(self, mock_client, ims):
        ims.send_sms(impu="sip:user@domain")
        mock_client.send.assert_called_once_with({
            "message": "sms",
            "impu": "sip:user@domain",
        })


class TestSmsFlush:
    def test_sends(self, mock_client, ims):
        ims.sms_flush()
        mock_client.send.assert_called_once_with({"message": "sms_flush"})


class TestSendMms:
    def test_sends(self, mock_client, ims):
        ims.send_mms(impu="sip:user@domain", filename="/tmp/pic.jpg")
        mock_client.send.assert_called_once_with({
            "message": "mms",
            "impu": "sip:user@domain",
            "filename": "/tmp/pic.jpg",
        })

    def test_with_extra_params(self, mock_client, ims):
        ims.send_mms(
            impu="sip:user@domain",
            filename="/tmp/pic.jpg",
            subject="Hi",
        )
        mock_client.send.assert_called_once_with({
            "message": "mms",
            "impu": "sip:user@domain",
            "filename": "/tmp/pic.jpg",
            "subject": "Hi",
        })


class TestMmsServer:
    def test_sends(self, mock_client, ims):
        ims.mms_server()
        mock_client.send.assert_called_once_with({"message": "mms_server"})


class TestLicense:
    def test_sends(self, mock_client, ims):
        ims.license()
        mock_client.send.assert_called_once_with({"message": "license"})


class TestIpsec:
    def test_sends(self, mock_client, ims):
        ims.ipsec()
        mock_client.send.assert_called_once_with({"message": "ipsec"})


class TestRegisterEvents:
    def test_sends(self, mock_client, ims):
        ims.register_events("sms", "dialog", "users_update")
        mock_client.send.assert_called_once_with({
            "message": "register",
            "register": ["sms", "dialog", "users_update"],
        })
