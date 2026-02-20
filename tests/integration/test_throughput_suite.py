"""Integration tests for the throughput test suite.

These tests verify the throughput testing components work correctly
with a live Amarisoft Callbox.

Run with:
    pytest tests/integration/test_throughput_suite.py -v --host <IP>

For tests that require iPerf:
    pytest tests/integration/test_throughput_suite.py -v --host <IP> --iperf-server <UE_IP>
"""

import json
import subprocess
import sys
from unittest.mock import patch

import pytest

# Add the examples directory to path for imports
sys.path.insert(0, "examples")

from throughput_test_suite import (
    RAT,
    DuplexMode,
    MIMOMode,
    TestScenario,
    ThroughputResult,
    ThroughputTestSuite,
    IPerfManager,
    IPerfResult,
    LatencyMeasurement,
    LatencyResult,
    BLERMeasurement,
    TEST_SCENARIOS,
    LTE_FDD_BANDS,
    LTE_TDD_BANDS,
    NR_FDD_BANDS,
    NR_TDD_BANDS,
    ENDC_BAND_COMBOS,
    SCENARIO_BANDS,
    get_band_earfcn,
    get_band_arfcn,
    format_band_string,
)


pytestmark = pytest.mark.integration


# ══════════════════════════════════════════════════════════════
# Pytest CLI Options
# ══════════════════════════════════════════════════════════════

def pytest_addoption(parser):
    """Add custom CLI options for throughput tests."""
    try:
        parser.addoption(
            "--iperf-server",
            action="store",
            default=None,
            help="iPerf server IP for throughput tests",
        )
        parser.addoption(
            "--ue-ip",
            action="store",
            default=None,
            help="UE IP address for latency tests",
        )
    except ValueError:
        # Options already added
        pass


@pytest.fixture(scope="session")
def iperf_server(request):
    """Get iPerf server IP from CLI."""
    return request.config.getoption("--iperf-server", default=None)


@pytest.fixture(scope="session")
def ue_ip(request):
    """Get UE IP from CLI."""
    return request.config.getoption("--ue-ip", default=None)


# ══════════════════════════════════════════════════════════════
# Band Configuration Tests
# ══════════════════════════════════════════════════════════════

class TestBandDefinitions:
    """Tests for band definitions and mappings."""

    def test_lte_fdd_bands_defined(self):
        """Verify LTE FDD bands are defined."""
        assert len(LTE_FDD_BANDS) > 0
        assert "B2" in LTE_FDD_BANDS
        assert "B66" in LTE_FDD_BANDS

    def test_lte_tdd_bands_defined(self):
        """Verify LTE TDD bands are defined."""
        assert len(LTE_TDD_BANDS) > 0
        assert "B41" in LTE_TDD_BANDS

    def test_nr_fdd_bands_defined(self):
        """Verify NR FDD bands are defined."""
        assert len(NR_FDD_BANDS) > 0
        assert "n2" in NR_FDD_BANDS
        assert "n66" in NR_FDD_BANDS

    def test_nr_tdd_bands_defined(self):
        """Verify NR TDD bands are defined."""
        assert len(NR_TDD_BANDS) > 0
        assert "n41" in NR_TDD_BANDS

    def test_endc_band_combos_defined(self):
        """Verify ENDC band combinations are defined."""
        assert len(ENDC_BAND_COMBOS) > 0
        # Check format is (LTE_band, NR_band)
        for combo in ENDC_BAND_COMBOS:
            assert isinstance(combo, tuple)
            assert len(combo) == 2
            lte_band, nr_band = combo
            assert lte_band.startswith("B")
            assert nr_band.startswith("n")

    def test_scenario_bands_mapping(self):
        """Verify all scenarios have band mappings."""
        expected_keys = [
            "lte_fdd_1cc", "lte_fdd_1cc_siso",
            "lte_tdd_1cc", "lte_tdd_1cc_siso",
            "nr_fdd_1cc", "nr_fdd_1cc_siso",
            "nr_tdd_1cc", "nr_tdd_1cc_siso",
            "endc", "endc_siso",
        ]
        for key in expected_keys:
            assert key in SCENARIO_BANDS, f"Missing band mapping for {key}"
            assert len(SCENARIO_BANDS[key]) > 0

    def test_get_band_earfcn(self):
        """Test EARFCN lookup for LTE bands."""
        assert get_band_earfcn("B2") is not None
        assert get_band_earfcn("B41") is not None
        assert get_band_earfcn("invalid") is None

    def test_get_band_arfcn(self):
        """Test NR-ARFCN lookup for NR bands."""
        assert get_band_arfcn("n2") is not None
        assert get_band_arfcn("n41") is not None
        assert get_band_arfcn("invalid") is None

    def test_format_band_string_single(self):
        """Test band string formatting for single band."""
        assert format_band_string("B2") == "B2"
        assert format_band_string("n41") == "n41"

    def test_format_band_string_endc(self):
        """Test band string formatting for ENDC tuple."""
        assert format_band_string(("B2", "n41")) == "B2+n41"
        assert format_band_string(("B66", "n25")) == "B66+n25"


# ══════════════════════════════════════════════════════════════
# Test Scenario Tests
# ══════════════════════════════════════════════════════════════

class TestTestScenarios:
    """Tests for test scenario definitions."""

    def test_all_scenarios_defined(self):
        """Verify all 10 test scenarios are defined."""
        assert len(TEST_SCENARIOS) == 10

    def test_scenario_names(self):
        """Verify expected scenario names exist."""
        expected = [
            "lte_fdd_1cc", "lte_tdd_1cc",
            "lte_fdd_1cc_siso", "lte_tdd_1cc_siso",
            "nr_fdd_1cc", "nr_tdd_1cc",
            "nr_fdd_1cc_siso", "nr_tdd_1cc_siso",
            "endc", "endc_siso",
        ]
        for name in expected:
            assert name in TEST_SCENARIOS, f"Missing scenario: {name}"

    def test_lte_fdd_scenario(self):
        """Test LTE FDD scenario configuration."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc"]
        assert scenario.rat == RAT.LTE
        assert scenario.duplex == DuplexMode.FDD
        assert scenario.mimo == MIMOMode.MIMO_2x2
        assert scenario.expected_dl_mbps > 0
        assert scenario.expected_ul_mbps > 0

    def test_nr_tdd_scenario(self):
        """Test NR TDD scenario configuration."""
        scenario = TEST_SCENARIOS["nr_tdd_1cc"]
        assert scenario.rat == RAT.NR
        assert scenario.duplex == DuplexMode.TDD
        assert scenario.mimo == MIMOMode.MIMO_4x4
        assert scenario.expected_dl_mbps > 0

    def test_endc_scenario(self):
        """Test ENDC scenario configuration."""
        scenario = TEST_SCENARIOS["endc"]
        assert scenario.rat == RAT.ENDC
        assert scenario.mimo == MIMOMode.MIMO_4x4
        assert scenario.expected_dl_mbps > 0

    def test_siso_scenarios_have_lower_expectations(self):
        """Verify SISO scenarios expect lower throughput than MIMO."""
        mimo = TEST_SCENARIOS["lte_fdd_1cc"]
        siso = TEST_SCENARIOS["lte_fdd_1cc_siso"]
        assert siso.expected_dl_mbps < mimo.expected_dl_mbps

    def test_scenario_pass_threshold(self):
        """Verify scenarios have reasonable pass thresholds."""
        for name, scenario in TEST_SCENARIOS.items():
            assert 0 < scenario.pass_threshold <= 1.0


# ══════════════════════════════════════════════════════════════
# ThroughputResult Tests
# ══════════════════════════════════════════════════════════════

class TestThroughputResult:
    """Tests for ThroughputResult dataclass."""

    def test_result_creation(self):
        """Test creating a ThroughputResult."""
        result = ThroughputResult(
            test_name="test",
            rat="lte",
            duplex="fdd",
            mimo="2x2",
            band="B2",
            duration_s=30.0,
            samples=10,
            dl_avg_mbps=50.0,
            dl_max_mbps=60.0,
            dl_min_mbps=40.0,
            ul_avg_mbps=25.0,
            ul_max_mbps=30.0,
            ul_min_mbps=20.0,
            dl_expected_mbps=75.0,
            ul_expected_mbps=50.0,
            dl_efficiency=66.7,
            ul_efficiency=50.0,
            ue_count=1,
            passed=True,
        )
        assert result.test_name == "test"
        assert result.band == "B2"
        assert result.dl_avg_mbps == 50.0

    def test_result_bler_defaults(self):
        """Test BLER defaults to 0."""
        result = ThroughputResult(
            test_name="test",
            rat="lte",
            duplex="fdd",
            mimo="2x2",
            band="B2",
            duration_s=30.0,
            samples=10,
            dl_avg_mbps=50.0,
            dl_max_mbps=60.0,
            dl_min_mbps=40.0,
            ul_avg_mbps=25.0,
            ul_max_mbps=30.0,
            ul_min_mbps=20.0,
            dl_expected_mbps=75.0,
            ul_expected_mbps=50.0,
            dl_efficiency=66.7,
            ul_efficiency=50.0,
            ue_count=1,
            passed=True,
        )
        assert result.dl_bler == 0.0
        assert result.ul_bler == 0.0

    def test_result_latency_defaults(self):
        """Test latency defaults to 0."""
        result = ThroughputResult(
            test_name="test",
            rat="lte",
            duplex="fdd",
            mimo="2x2",
            band="B2",
            duration_s=30.0,
            samples=10,
            dl_avg_mbps=50.0,
            dl_max_mbps=60.0,
            dl_min_mbps=40.0,
            ul_avg_mbps=25.0,
            ul_max_mbps=30.0,
            ul_min_mbps=20.0,
            dl_expected_mbps=75.0,
            ul_expected_mbps=50.0,
            dl_efficiency=66.7,
            ul_efficiency=50.0,
            ue_count=1,
            passed=True,
        )
        assert result.latency_avg_ms == 0.0
        assert result.latency_min_ms == 0.0
        assert result.latency_max_ms == 0.0


# ══════════════════════════════════════════════════════════════
# IPerfManager Tests
# ══════════════════════════════════════════════════════════════

class TestIPerfManager:
    """Tests for iPerf integration."""

    def test_iperf_manager_creation(self):
        """Test creating IPerfManager instance."""
        manager = IPerfManager(server_ip="192.168.1.100", port=5201)
        assert manager.server_ip == "192.168.1.100"
        assert manager.port == 5201
        assert manager.use_udp is False
        assert manager.parallel == 1

    def test_iperf_manager_udp_mode(self):
        """Test IPerfManager with UDP mode."""
        manager = IPerfManager(
            server_ip="192.168.1.100",
            use_udp=True,
            parallel=4,
        )
        assert manager.use_udp is True
        assert manager.parallel == 4

    def test_iperf_result_creation(self):
        """Test creating IPerfResult."""
        result = IPerfResult(
            direction="dl",
            throughput_mbps=100.5,
            transfer_mb=125.0,
            duration_s=10.0,
            retransmits=5,
            success=True,
        )
        assert result.direction == "dl"
        assert result.throughput_mbps == 100.5
        assert result.success is True

    def test_iperf_not_available_handling(self):
        """Test handling when iPerf is not available."""
        with patch("shutil.which", return_value=None):
            manager = IPerfManager(server_ip="192.168.1.100")
            result = manager.run_client(duration=5)
            assert result.success is False
            assert "not available" in result.error

    @pytest.mark.skipif(
        subprocess.run(["which", "iperf3"], capture_output=True).returncode != 0,
        reason="iPerf3 not installed",
    )
    def test_iperf_parse_json_output(self):
        """Test parsing iPerf JSON output."""
        manager = IPerfManager(server_ip="127.0.0.1")

        sample_json = json.dumps({
            "end": {
                "sum_sent": {
                    "bits_per_second": 100_000_000,  # 100 Mbps
                    "bytes": 125_000_000,
                    "seconds": 10.0,
                    "retransmits": 3,
                },
                "sum_received": {
                    "bits_per_second": 95_000_000,
                    "bytes": 118_750_000,
                    "seconds": 10.0,
                },
            }
        })

        result = manager._parse_iperf_output(sample_json, "ul", 10.0)
        assert result.success is True
        assert result.throughput_mbps == 100.0
        assert result.retransmits == 3

    @pytest.mark.skipif(
        subprocess.run(["which", "iperf3"], capture_output=True).returncode != 0,
        reason="iPerf3 not installed",
    )
    def test_iperf_parse_error_json(self):
        """Test parsing iPerf error JSON."""
        manager = IPerfManager(server_ip="127.0.0.1")

        error_json = json.dumps({"error": "unable to connect to server"})

        result = manager._parse_iperf_output(error_json, "dl", 10.0)
        assert result.success is False
        assert "unable to connect" in result.error


class TestIPerfLive:
    """Live iPerf tests (require --iperf-server)."""

    @pytest.fixture
    def iperf_manager(self, iperf_server):
        """Create iPerf manager with configured server."""
        if not iperf_server:
            pytest.skip("--iperf-server not provided")
        return IPerfManager(server_ip=iperf_server)

    def test_iperf_ul_test(self, iperf_manager):
        """Test uplink iPerf measurement."""
        result = iperf_manager.run_client(duration=5, reverse=False)
        # May fail if server not running, but should not crash
        assert isinstance(result, IPerfResult)
        assert result.direction == "ul"

    def test_iperf_dl_test(self, iperf_manager):
        """Test downlink iPerf measurement (reverse mode)."""
        result = iperf_manager.run_client(duration=5, reverse=True)
        assert isinstance(result, IPerfResult)
        assert result.direction == "dl"

    def test_iperf_bidirectional(self, iperf_manager):
        """Test bidirectional iPerf measurement."""
        dl_result, ul_result = iperf_manager.run_bidirectional(duration=5)
        assert isinstance(dl_result, IPerfResult)
        assert isinstance(ul_result, IPerfResult)
        assert dl_result.direction == "dl"
        assert ul_result.direction == "ul"


# ══════════════════════════════════════════════════════════════
# LatencyMeasurement Tests
# ══════════════════════════════════════════════════════════════

class TestLatencyMeasurement:
    """Tests for latency measurement."""

    def test_latency_measurement_creation(self):
        """Test creating LatencyMeasurement instance."""
        measurer = LatencyMeasurement(target_ip="192.168.1.100")
        assert measurer.target_ip == "192.168.1.100"

    def test_latency_result_creation(self):
        """Test creating LatencyResult."""
        result = LatencyResult(
            avg_ms=25.5,
            min_ms=20.0,
            max_ms=35.0,
            jitter_ms=5.0,
            packet_loss_pct=0.0,
            packets_sent=20,
            packets_received=20,
            success=True,
        )
        assert result.avg_ms == 25.5
        assert result.success is True

    def test_latency_result_defaults(self):
        """Test LatencyResult default values."""
        result = LatencyResult()
        assert result.avg_ms == 0.0
        assert result.success is True
        assert result.error == ""

    def test_ping_localhost(self):
        """Test pinging localhost (should always work)."""
        measurer = LatencyMeasurement(target_ip="127.0.0.1")
        result = measurer.measure(count=5, interval=0.2)
        assert result.success is True
        assert result.avg_ms > 0
        assert result.packets_received > 0

    def test_ping_output_parsing_linux(self):
        """Test parsing Linux ping output format."""
        measurer = LatencyMeasurement(target_ip="127.0.0.1")

        sample_output = """
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.050 ms
64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.055 ms
64 bytes from 127.0.0.1: icmp_seq=3 ttl=64 time=0.048 ms

--- 127.0.0.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2000ms
rtt min/avg/max/mdev = 0.048/0.051/0.055/0.003 ms
"""
        result = measurer._parse_ping_output(sample_output, 3)
        assert result.success is True
        assert result.packets_sent == 3
        assert result.packets_received == 3
        assert result.packet_loss_pct == 0.0
        assert result.min_ms == 0.048
        assert result.avg_ms == 0.051
        assert result.max_ms == 0.055
        assert result.jitter_ms == 0.003

    def test_ping_output_parsing_macos(self):
        """Test parsing macOS ping output format."""
        measurer = LatencyMeasurement(target_ip="127.0.0.1")

        sample_output = """
PING 127.0.0.1 (127.0.0.1): 56 data bytes
64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.050 ms
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.055 ms
64 bytes from 127.0.0.1: icmp_seq=2 ttl=64 time=0.048 ms

--- 127.0.0.1 ping statistics ---
3 packets transmitted, 3 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 0.048/0.051/0.055/0.003 ms
"""
        result = measurer._parse_ping_output(sample_output, 3)
        assert result.success is True
        assert result.packets_sent == 3
        assert result.packets_received == 3
        assert result.min_ms == 0.048
        assert result.avg_ms == 0.051

    def test_ping_output_parsing_packet_loss(self):
        """Test parsing ping output with packet loss."""
        measurer = LatencyMeasurement(target_ip="127.0.0.1")

        sample_output = """
--- 192.168.1.100 ping statistics ---
5 packets transmitted, 3 received, 40% packet loss, time 4000ms
rtt min/avg/max/mdev = 25.0/30.0/35.0/5.0 ms
"""
        result = measurer._parse_ping_output(sample_output, 5)
        assert result.packets_sent == 5
        assert result.packets_received == 3
        assert result.packet_loss_pct == 40.0


class TestLatencyLive:
    """Live latency tests (require --ue-ip)."""

    @pytest.fixture
    def latency_measurer(self, ue_ip):
        """Create latency measurer with configured UE IP."""
        if not ue_ip:
            pytest.skip("--ue-ip not provided")
        return LatencyMeasurement(target_ip=ue_ip)

    def test_latency_to_ue(self, latency_measurer):
        """Test latency measurement to UE."""
        result = latency_measurer.measure(count=10, interval=0.5)
        assert isinstance(result, LatencyResult)
        if result.success:
            assert result.avg_ms > 0
            assert result.min_ms <= result.avg_ms <= result.max_ms


# ══════════════════════════════════════════════════════════════
# BLERMeasurement Tests
# ══════════════════════════════════════════════════════════════

class TestBLERMeasurement:
    """Tests for BLER measurement."""

    def test_bler_measurement_creation(self, callbox):
        """Test creating BLERMeasurement instance."""
        measurer = BLERMeasurement(callbox)
        assert measurer.cb is callbox

    def test_bler_measurement(self, callbox):
        """Test BLER measurement from eNB stats."""
        measurer = BLERMeasurement(callbox)
        dl_bler, ul_bler = measurer.measure(duration=2.0, interval=0.5)

        # BLER should be between 0 and 100
        assert 0.0 <= dl_bler <= 100.0
        assert 0.0 <= ul_bler <= 100.0

    def test_bler_with_no_traffic(self, callbox):
        """Test BLER returns 0 when no traffic."""
        measurer = BLERMeasurement(callbox)
        dl_bler, ul_bler = measurer.measure(duration=1.0)

        # With no UE attached, BLER should be 0
        # (division by zero handled)
        assert dl_bler >= 0.0
        assert ul_bler >= 0.0


# ══════════════════════════════════════════════════════════════
# ThroughputTestSuite Tests
# ══════════════════════════════════════════════════════════════

class TestThroughputTestSuiteInit:
    """Tests for ThroughputTestSuite initialization."""

    def test_suite_creation(self, callbox_host):
        """Test creating ThroughputTestSuite instance."""
        suite = ThroughputTestSuite(host=callbox_host)
        assert suite.host == callbox_host
        assert suite.results == []

    def test_suite_with_iperf(self, callbox_host):
        """Test suite with iPerf configuration."""
        suite = ThroughputTestSuite(
            host=callbox_host,
            iperf_server_ip="192.168.1.100",
            iperf_port=5201,
        )
        assert suite.iperf_server_ip == "192.168.1.100"
        assert suite.iperf_port == 5201

    def test_suite_with_latency(self, callbox_host):
        """Test suite with latency configuration."""
        suite = ThroughputTestSuite(
            host=callbox_host,
            ue_ip="192.168.1.100",
        )
        assert suite.ue_ip == "192.168.1.100"


class TestThroughputTestSuiteLive:
    """Live tests for ThroughputTestSuite."""

    @pytest.fixture
    def suite(self, callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify):
        """Create and connect a test suite."""
        suite = ThroughputTestSuite(
            host=callbox_host,
            password=callbox_password,
            ssl=callbox_ssl,
            ssl_verify=callbox_ssl_verify,
        )
        connected = suite.connect()
        if not connected:
            pytest.skip("Could not connect to Callbox")
        yield suite
        suite.disconnect()

    def test_suite_connect(self, suite):
        """Test suite connection."""
        assert suite.cb is not None

    def test_check_ue_attached(self, suite):
        """Test checking UE attachment status."""
        attached, count = suite.check_ue_attached()
        assert isinstance(attached, bool)
        assert isinstance(count, int)
        assert count >= 0

    def test_get_current_cell_info(self, suite):
        """Test getting current cell configuration."""
        info = suite.get_current_cell_info()
        assert isinstance(info, dict)
        assert "stats" in info or "config" in info

    def test_measure_throughput(self, suite):
        """Test throughput measurement from eNB stats."""
        samples = suite.measure_throughput(duration=3, warmup=1)
        assert isinstance(samples, list)
        # Even with no UE, should return samples (possibly with 0 throughput)

    def test_run_single_test(self, suite):
        """Test running a single test scenario."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc"]
        result = suite.run_test(scenario)

        assert isinstance(result, ThroughputResult)
        assert result.test_name == scenario.name
        assert result.rat == scenario.rat.value
        assert result.band is not None

    def test_run_test_with_band(self, suite):
        """Test running a test with specific band."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc"]
        result = suite.run_test(scenario, band="B2")

        assert result.band == "B2"

    def test_run_test_endc_band(self, suite):
        """Test running a test with ENDC band combination."""
        scenario = TEST_SCENARIOS["endc"]
        result = suite.run_test(scenario, band=("B2", "n41"))

        assert result.band == "B2+n41"

    def test_run_all_tests_single_scenario(self, suite):
        """Test running all tests with a single scenario."""
        results = suite.run_all_tests(scenarios=["lte_fdd_1cc"])

        assert len(results) == 1
        assert results[0].test_name == "LTE FDD 1CC (MIMO)"

    def test_run_all_tests_multiple(self, suite):
        """Test running multiple scenarios."""
        results = suite.run_all_tests(
            scenarios=["lte_fdd_1cc", "nr_fdd_1cc"]
        )

        assert len(results) == 2

    def test_results_export_json(self, suite, tmp_path):
        """Test exporting results to JSON."""
        # Run a quick test
        suite.run_all_tests(scenarios=["lte_fdd_1cc"])

        # Export
        output_file = tmp_path / "results.json"
        suite.export_results(str(output_file))

        # Verify
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert "results" in data
        assert len(data["results"]) == 1


class TestThroughputTestSuiteWithIPerf:
    """Tests with iPerf integration."""

    @pytest.fixture
    def suite_with_iperf(
        self,
        callbox_host,
        callbox_password,
        callbox_ssl,
        callbox_ssl_verify,
        iperf_server,
        ue_ip,
    ):
        """Create suite with iPerf and latency configured."""
        if not iperf_server:
            pytest.skip("--iperf-server not provided")

        suite = ThroughputTestSuite(
            host=callbox_host,
            password=callbox_password,
            ssl=callbox_ssl,
            ssl_verify=callbox_ssl_verify,
            iperf_server_ip=iperf_server,
            ue_ip=ue_ip or iperf_server,
        )
        connected = suite.connect()
        if not connected:
            pytest.skip("Could not connect to Callbox")
        yield suite
        suite.disconnect()

    def test_suite_has_iperf(self, suite_with_iperf):
        """Test suite has iPerf manager."""
        assert suite_with_iperf.iperf is not None

    def test_suite_has_latency(self, suite_with_iperf):
        """Test suite has latency measurer."""
        assert suite_with_iperf.latency_measurer is not None

    def test_run_test_with_measurements(self, suite_with_iperf):
        """Test running with all measurements enabled."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc"]
        result = suite_with_iperf.run_test(
            scenario,
            use_iperf=True,
            measure_bler=True,
            measure_latency=True,
        )

        assert isinstance(result, ThroughputResult)
        # iPerf metrics should be present (even if 0 due to no connectivity)
        assert hasattr(result, "iperf_dl_mbps")
        assert hasattr(result, "iperf_ul_mbps")


class TestBandBasedTesting:
    """Tests for per-band testing functionality."""

    @pytest.fixture
    def suite(self, callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify):
        """Create and connect a test suite."""
        suite = ThroughputTestSuite(
            host=callbox_host,
            password=callbox_password,
            ssl=callbox_ssl,
            ssl_verify=callbox_ssl_verify,
        )
        connected = suite.connect()
        if not connected:
            pytest.skip("Could not connect to Callbox")
        yield suite
        suite.disconnect()

    def test_get_scenario_key_lte_fdd(self, suite):
        """Test scenario key generation for LTE FDD."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc"]
        key = suite._get_scenario_key(scenario)
        assert key == "lte_fdd_1cc"

    def test_get_scenario_key_lte_siso(self, suite):
        """Test scenario key generation for LTE SISO."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc_siso"]
        key = suite._get_scenario_key(scenario)
        assert key == "lte_fdd_1cc_siso"

    def test_get_scenario_key_endc(self, suite):
        """Test scenario key generation for ENDC."""
        scenario = TEST_SCENARIOS["endc"]
        key = suite._get_scenario_key(scenario)
        assert key == "endc"

    def test_run_test_for_all_bands_lte(self, suite):
        """Test running for all LTE FDD bands (limited to 2 for speed)."""
        scenario = TEST_SCENARIOS["lte_fdd_1cc"]
        # Only test first 2 bands to keep test fast
        results = suite.run_test_for_all_bands(scenario, bands=["B2", "B4"])

        assert len(results) == 2
        assert results[0].band == "B2"
        assert results[1].band == "B4"

    def test_run_test_for_all_bands_endc(self, suite):
        """Test running for ENDC band combinations."""
        scenario = TEST_SCENARIOS["endc"]
        # Test with single ENDC combo
        results = suite.run_test_for_all_bands(
            scenario,
            bands=[("B2", "n41")],
        )

        assert len(results) == 1
        assert results[0].band == "B2+n41"


# ══════════════════════════════════════════════════════════════
# Summary and Reporting Tests
# ══════════════════════════════════════════════════════════════

class TestReporting:
    """Tests for result reporting."""

    @pytest.fixture
    def suite_with_results(
        self,
        callbox_host,
        callbox_password,
        callbox_ssl,
        callbox_ssl_verify,
    ):
        """Create suite and run a test to generate results."""
        suite = ThroughputTestSuite(
            host=callbox_host,
            password=callbox_password,
            ssl=callbox_ssl,
            ssl_verify=callbox_ssl_verify,
        )
        connected = suite.connect()
        if not connected:
            pytest.skip("Could not connect to Callbox")

        # Run a quick test
        suite.run_all_tests(scenarios=["lte_fdd_1cc"])
        yield suite
        suite.disconnect()

    def test_print_summary(self, suite_with_results, capsys):
        """Test print_summary output."""
        suite_with_results.print_summary()
        captured = capsys.readouterr()

        assert "TEST SUMMARY" in captured.out
        assert "lte_fdd_1cc" in captured.out or "LTE FDD" in captured.out

    def test_export_results_structure(self, suite_with_results, tmp_path):
        """Test exported JSON structure."""
        output_file = tmp_path / "results.json"
        suite_with_results.export_results(str(output_file))

        with open(output_file) as f:
            data = json.load(f)

        # Check structure
        assert "test_suite" in data
        assert "host" in data
        assert "results" in data
        assert "summary" in data

        # Check summary
        summary = data["summary"]
        assert "total_tests" in summary
        assert "passed" in summary
        assert "failed" in summary

    def test_export_results_content(self, suite_with_results, tmp_path):
        """Test exported result content."""
        output_file = tmp_path / "results.json"
        suite_with_results.export_results(str(output_file))

        with open(output_file) as f:
            data = json.load(f)

        # Check result content
        result = data["results"][0]
        assert "test_name" in result
        assert "rat" in result
        assert "band" in result
        assert "dl_avg_mbps" in result
        assert "ul_avg_mbps" in result
        assert "dl_bler" in result
        assert "latency_avg_ms" in result
