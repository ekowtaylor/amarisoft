"""Tests for logging module."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from client.websocket.logging import (
    LogEntry,
    LogCollector,
    TestSession,
    TestStep,
    enable_file_logging,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_callbox():
    """Create a mock Callbox instance."""
    callbox = MagicMock()
    callbox.host = "192.168.1.80"
    callbox.status = {"enb": True, "mme": True, "ims": False, "ue": False}

    # Mock ENB API
    callbox.enb = MagicMock()
    callbox.enb.log_get.return_value = {"logs": []}
    callbox.enb.config_get.return_value = {"cell_id": 1}
    callbox.enb.stats.return_value = {"uptime": 1000}

    # Mock MME API
    callbox.mme = MagicMock()
    callbox.mme.log_get.return_value = {"logs": []}
    callbox.mme.config_get.return_value = {"plmn": "00101"}
    callbox.mme.stats.return_value = {"attached_ues": 0}

    return callbox


@pytest.fixture
def log_collector(mock_callbox):
    """Create a LogCollector instance."""
    return LogCollector(mock_callbox)


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ══════════════════════════════════════════════════════════════════════════════
# LOG ENTRY TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_basic_creation(self):
        entry = LogEntry(
            timestamp="2024-01-15T10:30:00",
            service="enb",
            layer="RRC",
            level="INFO",
            message="Test message",
        )

        assert entry.service == "enb"
        assert entry.layer == "RRC"
        assert entry.level == "INFO"

    def test_str_representation(self):
        entry = LogEntry(
            timestamp="2024-01-15T10:30:00",
            service="enb",
            layer="RRC",
            level="INFO",
            message="Test message",
        )

        result = str(entry)

        assert "2024-01-15T10:30:00" in result
        assert "enb" in result
        assert "RRC" in result
        assert "Test message" in result

    def test_to_dict(self):
        entry = LogEntry(
            timestamp="2024-01-15T10:30:00",
            service="enb",
            layer="RRC",
            level="INFO",
            message="Test message",
            index=42,
        )

        d = entry.to_dict()

        assert d["timestamp"] == "2024-01-15T10:30:00"
        assert d["service"] == "enb"
        assert d["index"] == 42

    def test_level_to_str_integer(self):
        assert LogEntry.level_to_str(0) == "NONE"
        assert LogEntry.level_to_str(1) == "ERROR"
        assert LogEntry.level_to_str(2) == "WARNING"
        assert LogEntry.level_to_str(3) == "INFO"
        assert LogEntry.level_to_str(4) == "DEBUG"
        assert LogEntry.level_to_str(5) == "TRACE"

    def test_level_to_str_string(self):
        assert LogEntry.level_to_str("info") == "INFO"
        assert LogEntry.level_to_str("ERROR") == "ERROR"
        assert LogEntry.level_to_str("debug") == "DEBUG"

    def test_level_to_str_unknown_integer(self):
        result = LogEntry.level_to_str(99)
        assert "LEVEL_99" in result


# ══════════════════════════════════════════════════════════════════════════════
# LOG COLLECTOR TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestLogCollector:
    """Tests for LogCollector class."""

    def test_init(self, mock_callbox):
        collector = LogCollector(mock_callbox)

        assert collector.callbox is mock_callbox
        assert collector.logs == []

    def test_collect_once_empty(self, log_collector, mock_callbox):
        result = log_collector.collect_once()

        assert result == []
        mock_callbox.enb.log_get.assert_called_once()
        mock_callbox.mme.log_get.assert_called_once()

    def test_collect_once_with_logs(self, log_collector, mock_callbox):
        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {
                    "timestamp": 1705315800000,
                    "layer": "RRC",
                    "level": 3,
                    "msg": "Test message",
                    "idx": 1,
                }
            ]
        }

        result = log_collector.collect_once()

        assert len(result) == 1
        assert result[0].layer == "RRC"
        assert result[0].level == "INFO"

    def test_collect_once_with_data_array(self, log_collector, mock_callbox):
        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {
                    "timestamp": 1705315800000,
                    "layer": "PHY",
                    "level": 4,
                    "data": ["line 1", "line 2"],
                    "idx": 1,
                }
            ]
        }

        result = log_collector.collect_once()

        assert len(result) == 1
        assert "line 1" in result[0].message
        assert "line 2" in result[0].message

    def test_collect_once_service_filter(self, log_collector, mock_callbox):
        log_collector.collect_once(services=["enb"])

        mock_callbox.enb.log_get.assert_called_once()
        mock_callbox.mme.log_get.assert_not_called()

    def test_collect_once_layer_filter(self, log_collector, mock_callbox):
        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {"timestamp": 1705315800000, "layer": "RRC", "level": 3, "msg": "RRC msg", "idx": 1},
                {"timestamp": 1705315800000, "layer": "PHY", "level": 3, "msg": "PHY msg", "idx": 2},
            ]
        }

        result = log_collector.collect_once(layers=["RRC"])

        assert len(result) == 1
        assert result[0].layer == "RRC"

    def test_logs_property(self, log_collector, mock_callbox):
        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {"timestamp": 1705315800000, "layer": "RRC", "level": 3, "msg": "Test", "idx": 1},
            ]
        }

        log_collector.collect_once()

        assert len(log_collector.logs) == 1

    def test_clear(self, log_collector, mock_callbox):
        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {"timestamp": 1705315800000, "layer": "RRC", "level": 3, "msg": "Test", "idx": 1},
            ]
        }
        log_collector.collect_once()
        assert len(log_collector.logs) == 1

        log_collector.clear()

        assert len(log_collector.logs) == 0

    def test_filter_logs_by_service(self, log_collector):
        log_collector._logs = [
            LogEntry(timestamp="t1", service="enb", layer="RRC", level="INFO", message="m1"),
            LogEntry(timestamp="t2", service="mme", layer="NAS", level="INFO", message="m2"),
        ]

        result = log_collector.filter_logs(service="enb")

        assert len(result) == 1
        assert result[0].service == "enb"

    def test_filter_logs_by_layer(self, log_collector):
        log_collector._logs = [
            LogEntry(timestamp="t1", service="enb", layer="RRC", level="INFO", message="m1"),
            LogEntry(timestamp="t2", service="enb", layer="PHY", level="INFO", message="m2"),
        ]

        result = log_collector.filter_logs(layer="RRC")

        assert len(result) == 1
        assert result[0].layer == "RRC"

    def test_filter_logs_by_level(self, log_collector):
        log_collector._logs = [
            LogEntry(timestamp="t1", service="enb", layer="RRC", level="INFO", message="m1"),
            LogEntry(timestamp="t2", service="enb", layer="RRC", level="ERROR", message="m2"),
        ]

        result = log_collector.filter_logs(level="ERROR")

        assert len(result) == 1
        assert result[0].level == "ERROR"

    def test_filter_logs_by_contains(self, log_collector):
        log_collector._logs = [
            LogEntry(timestamp="t1", service="enb", layer="RRC", level="INFO", message="Hello world"),
            LogEntry(timestamp="t2", service="enb", layer="RRC", level="INFO", message="Goodbye world"),
        ]

        result = log_collector.filter_logs(contains="hello")

        assert len(result) == 1
        assert "Hello" in result[0].message


class TestLogCollectorContinuous:
    """Tests for continuous log collection."""

    def test_start_continuous(self, log_collector):
        log_collector.start_continuous(interval=0.1)

        assert log_collector._collector_thread is not None
        assert log_collector._collector_thread.is_alive()

        log_collector.stop_continuous()

    def test_stop_continuous(self, log_collector):
        log_collector.start_continuous(interval=0.1)
        log_collector.stop_continuous()

        assert log_collector._collector_thread is None

    def test_start_continuous_already_running(self, log_collector):
        log_collector.start_continuous(interval=0.1)

        with pytest.raises(RuntimeError, match="already running"):
            log_collector.start_continuous()

        log_collector.stop_continuous()

    def test_continuous_with_callback(self, log_collector, mock_callbox):
        collected = []

        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {"timestamp": 1705315800000, "layer": "RRC", "level": 3, "msg": "Test", "idx": 1},
            ]
        }

        log_collector.start_continuous(interval=0.05, callback=lambda e: collected.append(e))
        time.sleep(0.15)  # Allow a few collection cycles
        log_collector.stop_continuous()

        assert len(collected) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# TEST STEP TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestTestStep:
    """Tests for TestStep dataclass."""

    def test_basic_creation(self):
        step = TestStep(name="Test step", start_time=time.time())

        assert step.name == "Test step"
        assert step.status == "running"
        assert step.end_time is None

    def test_duration_running(self):
        step = TestStep(name="Test", start_time=time.time() - 1.0)

        assert step.duration >= 1.0

    def test_duration_completed(self):
        start = time.time()
        step = TestStep(
            name="Test",
            start_time=start,
            end_time=start + 2.5,
        )

        assert step.duration == pytest.approx(2.5, rel=0.01)

    def test_to_dict(self):
        step = TestStep(
            name="Test step",
            start_time=1000.0,
            end_time=1005.0,
            status="passed",
        )

        d = step.to_dict()

        assert d["name"] == "Test step"
        assert d["status"] == "passed"
        assert d["duration_s"] == 5.0


# ══════════════════════════════════════════════════════════════════════════════
# TEST SESSION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestTestSession:
    """Tests for TestSession class."""

    def test_init(self, mock_callbox, temp_output_dir):
        session = TestSession(
            mock_callbox,
            name="test_session",
            output_dir=temp_output_dir,
        )

        assert session.name == "test_session"
        assert session.callbox is mock_callbox
        assert session._status == "not_started"

    def test_context_manager_success(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            assert session._status == "running"

        assert session._status == "passed"
        assert session._session_dir is not None
        assert session._session_dir.exists()

    def test_context_manager_failure(self, mock_callbox, temp_output_dir):
        with pytest.raises(ValueError):
            with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
                raise ValueError("Test error")

        assert session._status == "failed"
        assert session._error == "Test error"

    def test_step_context_manager(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            with session.add_step("Step 1") as step:
                time.sleep(0.01)

            assert len(session.steps) == 1
            assert session.steps[0].status == "passed"

    def test_step_failure(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            try:
                with session.add_step("Failing step"):
                    raise RuntimeError("Step failed")
            except RuntimeError:
                pass

            assert session.steps[0].status == "failed"
            assert "Step failed" in session.steps[0].error

    def test_folder_prefix(self, mock_callbox, temp_output_dir):
        with TestSession(
            mock_callbox,
            name="test_name",
            output_dir=temp_output_dir,
            folder_prefix="custom_prefix",
        ) as session:
            pass

        assert session._session_dir is not None
        assert "custom_prefix_" in session._session_dir.name
        assert "test_name" not in session._session_dir.name

    def test_duration(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            time.sleep(0.05)

        assert session.duration >= 0.05

    def test_logs_property(self, mock_callbox, temp_output_dir):
        mock_callbox.enb.log_get.return_value = {
            "logs": [
                {"timestamp": 1705315800000, "layer": "RRC", "level": 3, "msg": "Test", "idx": 1},
            ]
        }

        with TestSession(
            mock_callbox,
            name="test",
            output_dir=temp_output_dir,
            collect_interval=0.05,
        ) as session:
            time.sleep(0.1)  # Allow collection

        # Logs should be collected
        assert isinstance(session.logs, list)

    def test_export_diagnostics(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            with session.add_step("Test step"):
                pass

        # Check that files were created
        assert (session._session_dir / "session_info.json").exists()
        assert (session._session_dir / "summary.txt").exists()

    def test_export_diagnostics_content(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test_export", output_dir=temp_output_dir) as session:
            with session.add_step("Step 1"):
                pass

        # Read and verify session_info.json
        info = json.loads((session._session_dir / "session_info.json").read_text())

        assert info["name"] == "test_export"
        assert info["status"] == "passed"
        assert len(info["steps"]) == 1
        assert info["steps"][0]["name"] == "Step 1"

    def test_get_errors(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            session._collector._logs = [
                LogEntry(timestamp="t1", service="enb", layer="RRC", level="INFO", message="m1"),
                LogEntry(timestamp="t2", service="enb", layer="RRC", level="ERROR", message="m2"),
            ]

            errors = session.get_errors()

        assert len(errors) == 1
        assert errors[0].level == "ERROR"

    def test_get_warnings(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            session._collector._logs = [
                LogEntry(timestamp="t1", service="enb", layer="RRC", level="INFO", message="m1"),
                LogEntry(timestamp="t2", service="enb", layer="RRC", level="WARNING", message="m2"),
                LogEntry(timestamp="t3", service="enb", layer="RRC", level="WARN", message="m3"),
            ]

            warnings = session.get_warnings()

        assert len(warnings) == 2

    def test_add_step(self, mock_callbox, temp_output_dir):
        with TestSession(mock_callbox, name="test", output_dir=temp_output_dir) as session:
            with session.add_step("Custom step"):
                pass

            assert len(session.steps) == 1
            assert session.steps[0].name == "Custom step"


# ══════════════════════════════════════════════════════════════════════════════
# ENABLE FILE LOGGING TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestEnableFileLogging:
    """Tests for enable_file_logging function."""

    def test_creates_handler(self, temp_output_dir):
        log_file = temp_output_dir / "test.log"

        handler = enable_file_logging(log_file)

        assert handler is not None
        handler.close()

    def test_logs_to_file(self, temp_output_dir):
        import logging

        log_file = temp_output_dir / "test.log"
        # Create the file first to ensure the path exists
        log_file.touch()

        handler = enable_file_logging(log_file)

        logger = logging.getLogger("amarisoft")
        original_level = logger.level
        logger.setLevel(logging.DEBUG)

        try:
            logger.info("Test message")
            handler.flush()

            content = log_file.read_text()
            assert "Test message" in content
        finally:
            handler.close()
            logger.setLevel(original_level)
