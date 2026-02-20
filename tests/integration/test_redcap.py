"""Integration tests for RedCap (Reduced Capability) device testing.

These tests verify the RedCap testing components work correctly
with a live Amarisoft Callbox.

Run with:
    pytest tests/integration/test_redcap.py -v --host <IP>
"""

import json
import sys

import pytest

# Add the examples directory to path for imports
sys.path.insert(0, "examples")

from redcap_example import (
    RedCapType,
    RedCapBandwidth,
    RedCapTestScenario,
    RedCapTestResult,
    RedCapTestSuite,
    REDCAP_TEST_SCENARIOS,
    REDCAP_FR1_BANDS,
    REDCAP_FR2_BANDS,
    REDCAP_HD_FDD_BANDS,
    REDCAP_MAX_BW_FR1_MHZ,
    REDCAP_MAX_BW_FR2_MHZ,
    REDCAP_MAX_MIMO_LAYERS_FR1,
    REDCAP_MAX_MIMO_LAYERS_FR2,
)


pytestmark = pytest.mark.integration


# ══════════════════════════════════════════════════════════════
# RedCap Constants Tests
# ══════════════════════════════════════════════════════════════

class TestRedCapConstants:
    """Tests for RedCap constant definitions."""

    def test_redcap_fr1_bands_defined(self):
        """Verify FR1 RedCap bands are defined."""
        assert len(REDCAP_FR1_BANDS) > 0
        assert "n78" in REDCAP_FR1_BANDS
        assert "n41" in REDCAP_FR1_BANDS
        assert "n71" in REDCAP_FR1_BANDS

    def test_redcap_fr2_bands_defined(self):
        """Verify FR2 RedCap bands are defined."""
        assert len(REDCAP_FR2_BANDS) > 0
        assert "n257" in REDCAP_FR2_BANDS

    def test_redcap_hd_fdd_bands_defined(self):
        """Verify HD-FDD bands are defined."""
        assert len(REDCAP_HD_FDD_BANDS) > 0
        # All HD-FDD bands should be FDD bands (not TDD)
        for band in REDCAP_HD_FDD_BANDS:
            assert band.startswith("n")

    def test_redcap_max_bandwidth_fr1(self):
        """Verify FR1 max bandwidth is 20 MHz."""
        assert REDCAP_MAX_BW_FR1_MHZ == 20

    def test_redcap_max_bandwidth_fr2(self):
        """Verify FR2 max bandwidth is 100 MHz."""
        assert REDCAP_MAX_BW_FR2_MHZ == 100

    def test_redcap_max_mimo_layers(self):
        """Verify MIMO layer constraints."""
        assert REDCAP_MAX_MIMO_LAYERS_FR1 == 2
        assert REDCAP_MAX_MIMO_LAYERS_FR2 == 2

    def test_redcap_type_enum(self):
        """Test RedCapType enum values."""
        assert RedCapType.REDCAP_FR1.value == "redcap_fr1"
        assert RedCapType.REDCAP_FR2.value == "redcap_fr2"
        assert RedCapType.REDCAP_HD_FDD.value == "redcap_hd"

    def test_redcap_bandwidth_enum(self):
        """Test RedCapBandwidth enum values."""
        assert RedCapBandwidth.BW_5MHZ.value == 5
        assert RedCapBandwidth.BW_10MHZ.value == 10
        assert RedCapBandwidth.BW_20MHZ.value == 20
        assert RedCapBandwidth.BW_100MHZ.value == 100


# ══════════════════════════════════════════════════════════════
# RedCap Scenario Tests
# ══════════════════════════════════════════════════════════════

class TestRedCapScenarios:
    """Tests for RedCap test scenario definitions."""

    def test_all_scenarios_defined(self):
        """Verify all expected scenarios are defined."""
        expected_scenarios = [
            "redcap_fr1_20mhz",
            "redcap_fr1_10mhz",
            "redcap_fr1_5mhz",
            "redcap_fr1_1rx",
            "redcap_hd_fdd_n71",
            "redcap_hd_fdd_n5",
            "redcap_fr2_100mhz",
            "redcap_fr2_50mhz",
            "redcap_wearable",
            "redcap_industrial_sensor",
            "redcap_video_surveillance",
        ]
        for scenario in expected_scenarios:
            assert scenario in REDCAP_TEST_SCENARIOS

    def test_fr1_20mhz_scenario(self):
        """Test FR1 20MHz scenario configuration."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_fr1_20mhz"]
        assert scenario.redcap_type == RedCapType.REDCAP_FR1
        assert scenario.bandwidth_mhz == 20
        assert scenario.mimo_layers == 2
        assert scenario.half_duplex is False
        assert scenario.expected_dl_mbps > 0
        assert scenario.expected_ul_mbps > 0

    def test_fr1_1rx_scenario(self):
        """Test FR1 single Rx antenna scenario."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_fr1_1rx"]
        assert scenario.redcap_type == RedCapType.REDCAP_FR1
        assert scenario.mimo_layers == 1  # Single Rx

    def test_hd_fdd_scenario(self):
        """Test half-duplex FDD scenario."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_hd_fdd_n71"]
        assert scenario.redcap_type == RedCapType.REDCAP_HD_FDD
        assert scenario.half_duplex is True
        assert scenario.band == "n71"

    def test_fr2_scenario(self):
        """Test FR2 RedCap scenario."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_fr2_100mhz"]
        assert scenario.redcap_type == RedCapType.REDCAP_FR2
        assert scenario.bandwidth_mhz == 100
        assert scenario.band == "n257"

    def test_use_case_scenarios(self):
        """Test IoT use case specific scenarios."""
        # Wearable
        wearable = REDCAP_TEST_SCENARIOS["redcap_wearable"]
        assert wearable.bandwidth_mhz <= 20
        assert wearable.mimo_layers == 1

        # Industrial sensor
        sensor = REDCAP_TEST_SCENARIOS["redcap_industrial_sensor"]
        assert sensor.bandwidth_mhz <= 20
        assert sensor.mimo_layers == 1

        # Video surveillance
        video = REDCAP_TEST_SCENARIOS["redcap_video_surveillance"]
        assert video.bandwidth_mhz == 20
        assert video.mimo_layers == 2
        assert video.expected_ul_mbps >= 50  # Higher UL for video upload

    def test_scenario_bandwidth_within_limits(self):
        """Verify all scenarios respect RedCap bandwidth limits."""
        for name, scenario in REDCAP_TEST_SCENARIOS.items():
            if scenario.redcap_type in (RedCapType.REDCAP_FR1, RedCapType.REDCAP_HD_FDD):
                assert scenario.bandwidth_mhz <= REDCAP_MAX_BW_FR1_MHZ, \
                    f"{name} exceeds FR1 max bandwidth"
            elif scenario.redcap_type == RedCapType.REDCAP_FR2:
                assert scenario.bandwidth_mhz <= REDCAP_MAX_BW_FR2_MHZ, \
                    f"{name} exceeds FR2 max bandwidth"

    def test_scenario_mimo_within_limits(self):
        """Verify all scenarios respect RedCap MIMO limits."""
        for name, scenario in REDCAP_TEST_SCENARIOS.items():
            if scenario.redcap_type in (RedCapType.REDCAP_FR1, RedCapType.REDCAP_HD_FDD):
                assert scenario.mimo_layers <= REDCAP_MAX_MIMO_LAYERS_FR1, \
                    f"{name} exceeds FR1 max MIMO layers"
            elif scenario.redcap_type == RedCapType.REDCAP_FR2:
                assert scenario.mimo_layers <= REDCAP_MAX_MIMO_LAYERS_FR2, \
                    f"{name} exceeds FR2 max MIMO layers"


# ══════════════════════════════════════════════════════════════
# RedCap Result Tests
# ══════════════════════════════════════════════════════════════

class TestRedCapResult:
    """Tests for RedCapTestResult dataclass."""

    def test_result_creation(self):
        """Test creating a RedCapTestResult."""
        result = RedCapTestResult(
            scenario_name="test",
            redcap_type="redcap_fr1",
            band="n78",
            bandwidth_mhz=20,
            mimo_layers=2,
            half_duplex=False,
            dl_avg_mbps=100.0,
            dl_max_mbps=120.0,
            ul_avg_mbps=40.0,
            ul_max_mbps=50.0,
            expected_dl_mbps=150.0,
            expected_ul_mbps=50.0,
            dl_efficiency=66.7,
            ul_efficiency=80.0,
            passed=True,
        )
        assert result.scenario_name == "test"
        assert result.bandwidth_mhz == 20
        assert result.passed is True

    def test_result_defaults(self):
        """Test RedCapTestResult default values."""
        result = RedCapTestResult(
            scenario_name="test",
            redcap_type="redcap_fr1",
            band="n78",
            bandwidth_mhz=20,
            mimo_layers=2,
            half_duplex=False,
            dl_avg_mbps=0,
            dl_max_mbps=0,
            ul_avg_mbps=0,
            ul_max_mbps=0,
            expected_dl_mbps=0,
            expected_ul_mbps=0,
            dl_efficiency=0,
            ul_efficiency=0,
            passed=False,
        )
        assert result.attach_time_ms == 0.0
        assert result.registration_success is False
        assert result.power_idle_mw == 0.0
        assert result.power_active_mw == 0.0
        assert result.notes == ""

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = RedCapTestResult(
            scenario_name="test",
            redcap_type="redcap_fr1",
            band="n78",
            bandwidth_mhz=20,
            mimo_layers=2,
            half_duplex=False,
            dl_avg_mbps=100.0,
            dl_max_mbps=120.0,
            ul_avg_mbps=40.0,
            ul_max_mbps=50.0,
            expected_dl_mbps=150.0,
            expected_ul_mbps=50.0,
            dl_efficiency=66.7,
            ul_efficiency=80.0,
            passed=True,
        )
        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["scenario_name"] == "test"
        assert data["bandwidth_mhz"] == 20
        assert data["passed"] is True


# ══════════════════════════════════════════════════════════════
# RedCap Validation Tests
# ══════════════════════════════════════════════════════════════

class TestRedCapValidation:
    """Tests for RedCap configuration validation."""

    @pytest.fixture
    def suite(self, callbox_host):
        """Create test suite instance."""
        return RedCapTestSuite(host=callbox_host)

    def test_validate_valid_fr1_config(self, suite):
        """Test validation of valid FR1 configuration."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_FR1,
            band="n78",
            bandwidth_mhz=20,
            mimo_layers=2,
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is True
        assert error == ""

    def test_validate_invalid_fr1_bandwidth(self, suite):
        """Test validation rejects excessive FR1 bandwidth."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_FR1,
            band="n78",
            bandwidth_mhz=40,  # Exceeds 20 MHz limit
            mimo_layers=2,
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is False
        assert "bandwidth" in error.lower()

    def test_validate_invalid_fr1_mimo(self, suite):
        """Test validation rejects excessive FR1 MIMO layers."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_FR1,
            band="n78",
            bandwidth_mhz=20,
            mimo_layers=4,  # Exceeds 2 layer limit
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is False
        assert "mimo" in error.lower()

    def test_validate_valid_fr2_config(self, suite):
        """Test validation of valid FR2 configuration."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_FR2,
            band="n257",
            bandwidth_mhz=100,
            mimo_layers=2,
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is True

    def test_validate_invalid_fr2_bandwidth(self, suite):
        """Test validation rejects excessive FR2 bandwidth."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_FR2,
            band="n257",
            bandwidth_mhz=200,  # Exceeds 100 MHz limit
            mimo_layers=2,
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is False
        assert "bandwidth" in error.lower()

    def test_validate_valid_hd_fdd_config(self, suite):
        """Test validation of valid HD-FDD configuration."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_HD_FDD,
            band="n71",  # Valid HD-FDD band
            bandwidth_mhz=20,
            mimo_layers=1,
            half_duplex=True,
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is True

    def test_validate_invalid_hd_fdd_band(self, suite):
        """Test validation rejects invalid HD-FDD band."""
        scenario = RedCapTestScenario(
            name="test",
            description="Test scenario",
            redcap_type=RedCapType.REDCAP_HD_FDD,
            band="n41",  # TDD band, not HD-FDD capable
            bandwidth_mhz=20,
            mimo_layers=1,
            half_duplex=True,
        )
        valid, error = suite.validate_redcap_config(scenario)
        assert valid is False
        assert "hd-fdd" in error.lower() or "band" in error.lower()


# ══════════════════════════════════════════════════════════════
# RedCap Test Suite Live Tests
# ══════════════════════════════════════════════════════════════

class TestRedCapTestSuiteInit:
    """Tests for RedCapTestSuite initialization."""

    def test_suite_creation(self, callbox_host):
        """Test creating RedCapTestSuite instance."""
        suite = RedCapTestSuite(host=callbox_host)
        assert suite.host == callbox_host
        assert suite.results == []

    def test_suite_with_ssl(self, callbox_host):
        """Test suite with SSL configuration."""
        suite = RedCapTestSuite(
            host=callbox_host,
            ssl=True,
            ssl_verify=False,
        )
        assert suite.ssl is True
        assert suite.ssl_verify is False


class TestRedCapTestSuiteLive:
    """Live tests for RedCapTestSuite (require Callbox)."""

    @pytest.fixture
    def suite(self, callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify):
        """Create and connect a RedCap test suite."""
        suite = RedCapTestSuite(
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
        attached, count, info = suite.check_ue_attached()
        assert isinstance(attached, bool)
        assert isinstance(count, int)
        assert isinstance(info, dict)

    def test_run_single_test(self, suite):
        """Test running a single RedCap scenario."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_fr1_20mhz"]
        result = suite.run_test(scenario)

        assert isinstance(result, RedCapTestResult)
        assert result.scenario_name == scenario.name
        assert result.redcap_type == scenario.redcap_type.value
        assert result.bandwidth_mhz == scenario.bandwidth_mhz

    def test_run_multiple_tests(self, suite):
        """Test running multiple RedCap scenarios."""
        results = suite.run_all_tests(
            scenarios=["redcap_fr1_20mhz", "redcap_fr1_10mhz"]
        )

        assert len(results) == 2
        assert results[0].bandwidth_mhz == 20
        assert results[1].bandwidth_mhz == 10

    def test_results_export_json(self, suite, tmp_path):
        """Test exporting results to JSON."""
        # Run a quick test
        suite.run_all_tests(scenarios=["redcap_fr1_20mhz"])

        # Export
        output_file = tmp_path / "redcap_results.json"
        suite.export_results(str(output_file))

        # Verify
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 1


class TestRedCapThroughputMeasurement:
    """Tests for RedCap throughput measurement."""

    @pytest.fixture
    def suite(self, callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify):
        """Create and connect a RedCap test suite."""
        suite = RedCapTestSuite(
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

    def test_measure_throughput(self, suite):
        """Test throughput measurement."""
        samples = suite.measure_throughput(duration=3, interval=1)
        assert isinstance(samples, list)
        # Should have samples even without UE (values may be 0)

    def test_throughput_samples_structure(self, suite):
        """Test throughput sample structure."""
        samples = suite.measure_throughput(duration=2, interval=0.5)

        if samples:
            sample = samples[0]
            assert "timestamp" in sample
            assert "cell_id" in sample
            assert "dl_bitrate" in sample
            assert "ul_bitrate" in sample


# ══════════════════════════════════════════════════════════════
# RedCap Use Case Tests
# ══════════════════════════════════════════════════════════════

class TestRedCapUseCases:
    """Tests for specific RedCap use cases."""

    def test_wearable_profile_constraints(self):
        """Test wearable device profile meets expected constraints."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_wearable"]

        # Wearables should have minimal resource usage
        assert scenario.bandwidth_mhz <= 10  # Low bandwidth
        assert scenario.mimo_layers == 1     # Single antenna
        assert scenario.expected_dl_mbps <= 50  # Modest throughput

    def test_industrial_sensor_profile(self):
        """Test industrial sensor profile."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_industrial_sensor"]

        # Industrial sensors need reliable but not high-speed connectivity
        assert scenario.bandwidth_mhz <= 20
        assert scenario.mimo_layers <= 2

    def test_video_surveillance_profile(self):
        """Test video surveillance camera profile."""
        scenario = REDCAP_TEST_SCENARIOS["redcap_video_surveillance"]

        # Video cameras need higher uplink for streaming
        assert scenario.expected_ul_mbps >= 30  # Enough for HD video
        assert scenario.bandwidth_mhz == 20     # Max FR1 bandwidth
        assert scenario.mimo_layers == 2        # Better throughput

    def test_hd_fdd_power_optimization(self):
        """Test HD-FDD scenarios for power-sensitive devices."""
        hd_scenarios = [
            REDCAP_TEST_SCENARIOS["redcap_hd_fdd_n71"],
            REDCAP_TEST_SCENARIOS["redcap_hd_fdd_n5"],
        ]

        for scenario in hd_scenarios:
            assert scenario.half_duplex is True
            assert scenario.mimo_layers == 1  # Typically single Rx for HD-FDD
