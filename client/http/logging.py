"""Logging and diagnostics collection for Amarisoft Callbox test runs via HTTP.

This module provides the same functionality as the WebSocket logging module
but works with the HTTP client.

- TestSession: Context manager for end-to-end test runs with automatic log capture
- LogCollector: Collects logs from all services during test execution
- DiagnosticsBundle: Exports all diagnostics (logs, stats, config) to files

Usage::

    from client.http import Callbox
    from client.http.logging import TestSession

    cb = Callbox("http://192.168.1.80:9010")
    with TestSession(cb, name="throughput_test") as session:
        # Run your tests here
        cb.enb.cell_gain(cell_id=1, gain=-10)
        # ... more test steps ...

    # Logs are automatically saved to ./logs/throughput_test_<timestamp>/
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .callbox import Callbox

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """A single log entry from a service."""

    timestamp: str
    service: str
    layer: str
    level: str
    message: str
    index: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    LEVEL_MAP = {
        0: "NONE",
        1: "ERROR",
        2: "WARNING",
        3: "INFO",
        4: "DEBUG",
        5: "TRACE",
    }

    def __str__(self) -> str:
        return f"[{self.timestamp}] [{self.service}:{self.layer}] {self.level}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "service": self.service,
            "layer": self.layer,
            "level": self.level,
            "message": self.message,
            "index": self.index,
        }

    @classmethod
    def level_to_str(cls, level: int | str) -> str:
        """Convert integer level to string."""
        if isinstance(level, str):
            return level.upper()
        return cls.LEVEL_MAP.get(level, f"LEVEL_{level}")


class LogCollector:
    """Collects logs from Callbox services via HTTP.

    Supports both polling and continuous collection modes.
    """

    def __init__(self, callbox: "Callbox"):
        """Initialize the log collector.

        Args:
            callbox: Connected HTTP Callbox instance.
        """
        self.callbox = callbox
        self._logs: list[LogEntry] = []
        self._log_indices: dict[str, int] = {
            "enb": 0,
            "mme": 0,
            "ims": 0,
            "ue": 0,
        }
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._collector_thread: threading.Thread | None = None

    def collect_once(
        self,
        services: list[str] | None = None,
        layers: list[str] | None = None,
    ) -> list[LogEntry]:
        """Collect logs from all services once.

        Args:
            services: List of services to collect from. Default: ["enb", "mme", "ims", "ue"].
            layers: Filter by layer names (e.g., ["PHY", "RRC", "NAS"]).

        Returns:
            List of new log entries.
        """
        if services is None:
            services = ["enb", "mme", "ims", "ue"]

        new_entries = []

        for service in services:
            try:
                api = getattr(self.callbox, service, None)
                if api is None:
                    continue

                # Get logs starting from last known index
                min_idx = self._log_indices.get(service, 0)
                result = api.log_get(min_=min_idx)

                log_list = result.get("logs", result.get("log_list", []))
                for log in log_list:
                    entry = self._parse_log_entry(log, service)
                    if layers is None or entry.layer in layers:
                        new_entries.append(entry)

                    # Update index
                    if entry.index >= self._log_indices.get(service, 0):
                        self._log_indices[service] = entry.index + 1

            except Exception as e:
                logger.warning(f"Failed to collect logs from {service}: {e}")

        with self._lock:
            self._logs.extend(new_entries)

        return new_entries

    def _parse_log_entry(self, log: dict[str, Any], service: str) -> LogEntry:
        """Parse a log entry from the API response."""
        raw_msg = log.get("msg", log.get("message", ""))
        if not raw_msg and "data" in log:
            data = log["data"]
            if isinstance(data, list):
                raw_msg = " ".join(str(d) for d in data)
            else:
                raw_msg = str(data)

        ts = log.get("time", log.get("timestamp", ""))
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(ts / 1000).isoformat()

        level = log.get("level", "INFO")
        level_str = LogEntry.level_to_str(level)

        return LogEntry(
            timestamp=str(ts),
            service=service,
            layer=log.get("layer", "UNKNOWN"),
            level=level_str,
            message=raw_msg,
            index=log.get("idx", log.get("index", 0)),
            raw=log,
        )

    def start_continuous(
        self,
        interval: float = 1.0,
        services: list[str] | None = None,
        callback: Callable[[LogEntry], None] | None = None,
    ) -> None:
        """Start continuous log collection in a background thread.

        Args:
            interval: Polling interval in seconds.
            services: Services to collect from.
            callback: Optional callback for each new log entry.
        """
        if self._collector_thread is not None:
            raise RuntimeError("Continuous collection already running")

        self._stop_event.clear()

        def collector_loop():
            while not self._stop_event.is_set():
                try:
                    entries = self.collect_once(services=services)
                    if callback:
                        for entry in entries:
                            callback(entry)
                except Exception as e:
                    logger.error(f"Log collection error: {e}")
                self._stop_event.wait(interval)

        self._collector_thread = threading.Thread(
            target=collector_loop,
            name="HTTPLogCollector",
            daemon=True,
        )
        self._collector_thread.start()
        logger.info("Started continuous log collection via HTTP")

    def stop_continuous(self) -> None:
        """Stop continuous log collection."""
        if self._collector_thread is None:
            return

        self._stop_event.set()
        self._collector_thread.join(timeout=5.0)
        self._collector_thread = None
        logger.info("Stopped continuous log collection")

    @property
    def logs(self) -> list[LogEntry]:
        """Return all collected logs."""
        with self._lock:
            return list(self._logs)

    def clear(self) -> None:
        """Clear all collected logs."""
        with self._lock:
            self._logs.clear()
            self._log_indices = {k: 0 for k in self._log_indices}

    def filter_logs(
        self,
        service: str | None = None,
        layer: str | None = None,
        level: str | None = None,
        contains: str | None = None,
    ) -> list[LogEntry]:
        """Filter collected logs.

        Args:
            service: Filter by service name.
            layer: Filter by layer name.
            level: Filter by log level.
            contains: Filter by message content.

        Returns:
            Filtered list of log entries.
        """
        with self._lock:
            filtered = self._logs

            if service:
                filtered = [e for e in filtered if e.service == service]
            if layer:
                filtered = [e for e in filtered if e.layer == layer]
            if level:
                filtered = [e for e in filtered if e.level.upper() == level.upper()]
            if contains:
                filtered = [e for e in filtered if contains.lower() in e.message.lower()]

            return list(filtered)


@dataclass
class TestStep:
    """A single step in a test execution."""

    name: str
    start_time: float
    end_time: float | None = None
    status: str = "running"
    error: str | None = None
    result: Any = None

    @property
    def duration(self) -> float:
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": self.duration,
            "status": self.status,
            "error": self.error,
        }


class TestSession:
    """Context manager for end-to-end test runs with automatic log capture via HTTP.

    Features:
    - Automatic log collection during test execution
    - Step tracking with timing
    - Diagnostics bundle export (logs, stats, config)
    - Failure analysis helpers

    Example::

        from client.http import Callbox
        from client.http.logging import TestSession

        cb = Callbox("http://192.168.1.80:9010")
        with TestSession(cb, name="my_test") as session:
            with session.step("Configure RF"):
                cb.enb.cell_gain(cell_id=1, gain=-10)

            with session.step("Check Stats"):
                stats = cb.enb.stats()

        # Session automatically exports:
        # ./logs/my_test_20260217_163000/
        #   ├── session_info.json
        #   ├── logs_enb.txt
        #   ├── logs_mme.txt
        #   ├── config_enb.json
        #   ├── config_mme.json
        #   ├── stats_final.json
        #   └── summary.txt
    """

    def __init__(
        self,
        callbox: "Callbox",
        name: str = "test_session",
        output_dir: str | Path | None = None,
        folder_prefix: str | None = None,
        collect_interval: float = 1.0,
        auto_export: bool = True,
        collect_on_error: bool = True,
    ):
        """Initialize a test session.

        Args:
            callbox: HTTP Callbox instance.
            name: Test session name (used for logging and identification).
            output_dir: Base directory for logs. Default: ./logs/
            folder_prefix: Optional prefix for the output folder name.
            collect_interval: Log polling interval in seconds.
            auto_export: Automatically export diagnostics on session end.
            collect_on_error: Collect extra diagnostics on test failure.
        """
        self.callbox = callbox
        self.name = name
        self.output_dir = Path(output_dir or "./logs")
        self.folder_prefix = folder_prefix
        self.collect_interval = collect_interval
        self.auto_export = auto_export
        self.collect_on_error = collect_on_error

        self._collector = LogCollector(callbox)
        self._steps: list[TestStep] = []
        self._current_step: TestStep | None = None
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._status = "not_started"
        self._error: str | None = None
        self._session_dir: Path | None = None

        self._initial_stats: dict[str, Any] = {}
        self._initial_config: dict[str, Any] = {}
        self._final_stats: dict[str, Any] = {}

    def __enter__(self) -> "TestSession":
        """Start the test session."""
        self._start_time = time.time()
        self._status = "running"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.folder_prefix if self.folder_prefix else self.name
        self._session_dir = self.output_dir / f"{prefix}_{timestamp}"
        self._session_dir.mkdir(parents=True, exist_ok=True)

        self._capture_initial_state()

        self._collector.start_continuous(
            interval=self.collect_interval,
            callback=self._log_callback,
        )

        logger.info(f"Started test session: {self.name}")
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        """End the test session."""
        self._end_time = time.time()

        self._collector.stop_continuous()
        self._collector.collect_once()
        self._capture_final_state()

        if exc_type is not None:
            self._status = "failed"
            self._error = str(exc_val)
            if self.collect_on_error:
                self._collect_error_diagnostics()
        elif any(s.status == "failed" for s in self._steps):
            self._status = "failed"
        else:
            self._status = "passed"

        if self.auto_export:
            self.export_diagnostics()

        logger.info(
            f"Test session {self.name} completed: {self._status} "
            f"({self.duration:.2f}s)"
        )

        return False

    def _log_callback(self, entry: LogEntry) -> None:
        """Called for each new log entry during collection."""
        pass

    def _capture_initial_state(self) -> None:
        """Capture initial configuration and stats."""
        for service in ["enb", "mme", "ims", "ue"]:
            try:
                api = getattr(self.callbox, service)
                self._initial_config[service] = api.config_get()
                self._initial_stats[service] = api.stats()
            except Exception as e:
                logger.warning(f"Failed to capture initial state for {service}: {e}")

    def _capture_final_state(self) -> None:
        """Capture final stats."""
        for service in ["enb", "mme", "ims", "ue"]:
            try:
                api = getattr(self.callbox, service)
                self._final_stats[service] = api.stats()
            except Exception as e:
                logger.warning(f"Failed to capture final state for {service}: {e}")

    def _collect_error_diagnostics(self) -> None:
        """Collect extra diagnostics on error."""
        try:
            self._error_ues_enb = self.callbox.enb.ue_get()
            self._error_ues_mme = self.callbox.mme.ue_get()
        except Exception as e:
            logger.warning(f"Failed to collect error diagnostics: {e}")

    @property
    def duration(self) -> float:
        """Session duration in seconds."""
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.time()
        return end - self._start_time

    @property
    def logs(self) -> list[LogEntry]:
        """All collected log entries."""
        return self._collector.logs

    @property
    def steps(self) -> list[TestStep]:
        """All test steps."""
        return list(self._steps)

    class step:
        """Context manager for a test step."""

        def __init__(self, session: "TestSession", name: str):
            self.session = session
            self.name = name
            self._step: TestStep | None = None

        def __enter__(self) -> TestStep:
            self._step = TestStep(name=self.name, start_time=time.time())
            self.session._steps.append(self._step)
            self.session._current_step = self._step
            logger.info(f"Step started: {self.name}")
            return self._step

        def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
            if self._step is None:
                return False

            self._step.end_time = time.time()

            if exc_type is not None:
                self._step.status = "failed"
                self._step.error = str(exc_val)
                logger.error(f"Step failed: {self.name} - {exc_val}")
            else:
                self._step.status = "passed"
                logger.info(f"Step passed: {self.name} ({self._step.duration:.2f}s)")

            self.session._current_step = None
            return False

    def add_step(self, name: str) -> "TestSession.step":
        """Add a test step.

        Args:
            name: Step name/description.

        Returns:
            Context manager for the step.
        """
        return TestSession.step(self, name)

    def export_diagnostics(self, output_dir: Path | None = None) -> Path:
        """Export all diagnostics to files.

        Args:
            output_dir: Override output directory.

        Returns:
            Path to the diagnostics directory.
        """
        export_dir = output_dir or self._session_dir
        if export_dir is None:
            export_dir = self.output_dir / f"{self.name}_{int(time.time())}"
        export_dir.mkdir(parents=True, exist_ok=True)

        session_info = {
            "name": self.name,
            "status": self._status,
            "error": self._error,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "duration_s": self.duration,
            "steps": [s.to_dict() for s in self._steps],
            "callbox_url": self.callbox.base_url,
        }
        (export_dir / "session_info.json").write_text(
            json.dumps(session_info, indent=2, default=str)
        )

        for service in ["enb", "mme", "ims", "ue"]:
            service_logs = self._collector.filter_logs(service=service)
            if service_logs:
                log_content = "\n".join(str(entry) for entry in service_logs)
                (export_dir / f"logs_{service}.txt").write_text(log_content)

        all_logs = sorted(self._collector.logs, key=lambda e: e.timestamp)
        if all_logs:
            log_content = "\n".join(str(entry) for entry in all_logs)
            (export_dir / "logs_all.txt").write_text(log_content)

        logs_json = [e.to_dict() for e in all_logs]
        (export_dir / "logs_all.json").write_text(
            json.dumps(logs_json, indent=2, default=str)
        )

        if self._initial_config:
            (export_dir / "config_initial.json").write_text(
                json.dumps(self._initial_config, indent=2, default=str)
            )

        if self._initial_stats:
            (export_dir / "stats_initial.json").write_text(
                json.dumps(self._initial_stats, indent=2, default=str)
            )

        if self._final_stats:
            (export_dir / "stats_final.json").write_text(
                json.dumps(self._final_stats, indent=2, default=str)
            )

        summary = self._generate_summary()
        (export_dir / "summary.txt").write_text(summary)

        logger.info(f"Exported diagnostics to: {export_dir}")
        return export_dir

    def _generate_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "=" * 60,
            f"TEST SESSION: {self.name}",
            "=" * 60,
            "",
            f"Status: {self._status.upper()}",
            f"Duration: {self.duration:.2f}s",
            f"Start: {datetime.fromtimestamp(self._start_time or 0).isoformat()}",
            f"End: {datetime.fromtimestamp(self._end_time or 0).isoformat()}",
            "",
        ]

        if self._error:
            lines.extend([
                "Error:",
                f"  {self._error}",
                "",
            ])

        lines.extend([
            "-" * 60,
            "STEPS",
            "-" * 60,
        ])

        for i, step in enumerate(self._steps, 1):
            status_icon = "✓" if step.status == "passed" else "✗" if step.status == "failed" else "○"
            lines.append(f"  {i}. [{status_icon}] {step.name} ({step.duration:.2f}s)")
            if step.error:
                lines.append(f"       Error: {step.error}")

        lines.extend([
            "",
            "-" * 60,
            "LOG SUMMARY",
            "-" * 60,
        ])

        for service in ["enb", "mme", "ims", "ue"]:
            service_logs = self._collector.filter_logs(service=service)
            if service_logs:
                error_count = len([log for log in service_logs if log.level.upper() == "ERROR"])
                warn_count = len([log for log in service_logs if log.level.upper() in ("WARN", "WARNING")])
                lines.append(f"  {service.upper()}: {len(service_logs)} entries ({error_count} errors, {warn_count} warnings)")

        lines.extend([
            "",
            "-" * 60,
            "FILES",
            "-" * 60,
            f"  Output directory: {self._session_dir}",
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    def get_errors(self) -> list[LogEntry]:
        """Get all error-level log entries."""
        return self._collector.filter_logs(level="ERROR")

    def get_warnings(self) -> list[LogEntry]:
        """Get all warning-level log entries."""
        return [
            e for e in self._collector.logs
            if e.level.upper() in ("WARN", "WARNING")
        ]


def enable_file_logging(
    log_file: str | Path = "amarisoft_http.log",
    level: int = logging.DEBUG,
    format_str: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
) -> logging.FileHandler:
    """Enable logging to a file for the HTTP client package.

    Args:
        log_file: Path to log file.
        level: Logging level.
        format_str: Log format string.

    Returns:
        The file handler (for later removal if needed).
    """
    handler = logging.FileHandler(log_file)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format_str))

    client_logger = logging.getLogger("client.http")
    client_logger.addHandler(handler)
    client_logger.setLevel(min(client_logger.level or logging.DEBUG, level))

    return handler
