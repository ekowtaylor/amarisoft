"""Tests for ServiceApi base class methods."""

from __future__ import annotations


class TestConfigGet:
    def test_sends_config_get(self, mock_client, enb):
        enb.config_get()
        mock_client.send.assert_called_once_with({"message": "config_get"})


class TestConfigSet:
    def test_sends_config_set_with_params(self, mock_client, enb):
        enb.config_set(foo=1, bar="baz")
        mock_client.send.assert_called_once_with(
            {"message": "config_set", "foo": 1, "bar": "baz"}
        )

    def test_sends_config_set_no_params(self, mock_client, enb):
        enb.config_set()
        mock_client.send.assert_called_once_with({"message": "config_set"})


class TestStats:
    def test_sends_stats_basic(self, mock_client, mme):
        mme.stats()
        mock_client.send.assert_called_once_with({"message": "stats"})

    def test_sends_stats_with_params(self, mock_client, mme):
        mme.stats(samples=True)
        mock_client.send.assert_called_once_with(
            {"message": "stats", "samples": True}
        )


class TestUeGet:
    def test_sends_ue_get_basic(self, mock_client, enb):
        enb.ue_get()
        mock_client.send.assert_called_once_with({"message": "ue_get"})

    def test_sends_ue_get_with_filter(self, mock_client, enb):
        enb.ue_get(imsi="001010123456789")
        mock_client.send.assert_called_once_with(
            {"message": "ue_get", "imsi": "001010123456789"}
        )


class TestLogGet:
    def test_sends_log_get_basic(self, mock_client, enb):
        enb.log_get()
        mock_client.send.assert_called_once_with({"message": "log_get"})

    def test_sends_log_get_with_params(self, mock_client, enb):
        enb.log_get(min_=0, max_=100, layer="PHY")
        mock_client.send.assert_called_once_with(
            {"message": "log_get", "min": 0, "max": 100, "layer": "PHY"}
        )

    def test_sends_log_get_with_timeout(self, mock_client, enb):
        enb.log_get(timeout=5.0)
        mock_client.send.assert_called_once_with(
            {"message": "log_get", "timeout": 5.0}
        )


class TestLogSet:
    def test_sends_log_set_with_layers(self, mock_client, enb):
        enb.log_set(layers={"PHY": {"level": "debug"}})
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "logs": {"layers": {"PHY": {"level": "debug"}}},
        })

    def test_sends_log_set_with_kwargs(self, mock_client, enb):
        enb.log_set(max_size=10)
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "logs": {"max_size": 10},
        })


class TestVersion:
    def test_sends_version(self, mock_client, enb):
        enb.version()
        mock_client.send.assert_called_once_with({"message": "version"})


class TestHelp:
    def test_sends_help(self, mock_client, enb):
        enb.help()
        mock_client.send.assert_called_once_with({"message": "help"})
