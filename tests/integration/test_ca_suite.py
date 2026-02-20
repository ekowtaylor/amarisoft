"""Integration tests for the Carrier Aggregation (CA) test suite.

These tests verify the CA testing components work correctly
with a live Amarisoft Callbox.

Run with:
    pytest tests/integration/test_ca_suite.py -v --host <IP>

For unit tests (no callbox required):
    pytest tests/integration/test_ca_suite.py -v -k "not Live"
"""

import json
import pytest
from pathlib import Path

# Import from the CA test suite module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples"))

from ca_test_suite import (
    # Enums
    CAType,
    CABandType,
    CellRole,
    # Data classes
    CarrierConfig,
    CAConfiguration,
    CarrierResult,
    CATestResult,
    # Band combinations
    LTE_CA_COMBINATIONS,
    NR_CA_COMBINATIONS,
    ENDC_COMBINATIONS,
    # EARFCN/ARFCN mappings
    LTE_EARFCN_MAP,
    NR_ARFCN_MAP,
    DEFAULT_BANDWIDTH,
    get_earfcn,
    get_arfcn,
    get_default_bandwidth,
    # Scenario builders
    create_lte_ca_config,
    create_nr_ca_config,
    create_endc_config,
    # Test scenarios
    CA_TEST_SCENARIOS,
    # Test suite
    CATestSuite,
)


# ══════════════════════════════════════════════════════════════
# TEST: ENUMS
# ══════════════════════════════════════════════════════════════

class TestCAEnums:
    """Test CA-related enumerations."""

    def test_ca_type_values(self):
        """Test CAType enum values."""
        assert CAType.LTE_CA.value == "lte_ca"
        assert CAType.NR_CA.value == "nr_ca"
        assert CAType.ENDC.value == "endc"
        assert CAType.NRDC.value == "nrdc"

    def test_ca_band_type_values(self):
        """Test CABandType enum values."""
        assert CABandType.INTRA_BAND_CONTIGUOUS.value == "intra_contig"
        assert CABandType.INTRA_BAND_NON_CONTIGUOUS.value == "intra_non_contig"
        assert CABandType.INTER_BAND.value == "inter_band"

    def test_cell_role_values(self):
        """Test CellRole enum values."""
        assert CellRole.PCELL.value == "pcell"
        assert CellRole.PSCELL.value == "pscell"
        assert CellRole.SCELL.value == "scell"


# ══════════════════════════════════════════════════════════════
# TEST: BAND COMBINATIONS
# ══════════════════════════════════════════════════════════════

class TestBandCombinations:
    """Test CA band combinations."""

    def test_lte_ca_combinations_defined(self):
        """Test LTE CA combinations are defined."""
        assert len(LTE_CA_COMBINATIONS) > 0
        # Check for common 2CC combinations
        assert "CA_2A-4A" in LTE_CA_COMBINATIONS
        assert "CA_2A-66A" in LTE_CA_COMBINATIONS

    def test_lte_ca_combination_structure(self):
        """Test LTE CA combination structure."""
        combo = LTE_CA_COMBINATIONS["CA_2A-4A"]
        assert "bands" in combo
        assert "type" in combo
        assert "max_bw" in combo
        assert combo["bands"] == ["B2", "B4"]
        assert combo["type"] == CABandType.INTER_BAND

    def test_lte_ca_intra_band_combinations(self):
        """Test intra-band LTE CA combinations."""
        assert "CA_41C" in LTE_CA_COMBINATIONS
        combo = LTE_CA_COMBINATIONS["CA_41C"]
        assert combo["type"] == CABandType.INTRA_BAND_CONTIGUOUS
        assert combo["bands"] == ["B41", "B41"]

    def test_lte_ca_multi_cc_combinations(self):
        """Test 3CC, 4CC, 5CC combinations."""
        # 3CC
        assert "CA_2A-4A-5A" in LTE_CA_COMBINATIONS
        assert len(LTE_CA_COMBINATIONS["CA_2A-4A-5A"]["bands"]) == 3

        # 4CC
        assert "CA_2A-4A-12A-66A" in LTE_CA_COMBINATIONS
        assert len(LTE_CA_COMBINATIONS["CA_2A-4A-12A-66A"]["bands"]) == 4

        # 5CC
        assert "CA_2A-4A-5A-12A-66A" in LTE_CA_COMBINATIONS
        assert len(LTE_CA_COMBINATIONS["CA_2A-4A-5A-12A-66A"]["bands"]) == 5

    def test_nr_ca_combinations_defined(self):
        """Test NR CA combinations are defined."""
        assert len(NR_CA_COMBINATIONS) > 0
        # Check for common combinations
        assert "CA_n2A-n66A" in NR_CA_COMBINATIONS
        assert "CA_n41C" in NR_CA_COMBINATIONS

    def test_nr_ca_fr1_combinations(self):
        """Test NR FR1 CA combinations."""
        combo = NR_CA_COMBINATIONS["CA_n2A-n66A"]
        assert combo["type"] == CABandType.INTER_BAND
        assert "n2" in combo["bands"]
        assert "n66" in combo["bands"]

    def test_nr_ca_fr2_combinations(self):
        """Test NR FR2 (mmWave) CA combinations."""
        assert "CA_n257C" in NR_CA_COMBINATIONS
        combo = NR_CA_COMBINATIONS["CA_n257C"]
        assert combo["type"] == CABandType.INTRA_BAND_CONTIGUOUS
        assert combo["max_bw"] == 800  # 800 MHz for FR2

    def test_endc_combinations_defined(self):
        """Test EN-DC combinations are defined."""
        assert len(ENDC_COMBINATIONS) > 0
        assert "DC_2A_n41A" in ENDC_COMBINATIONS

    def test_endc_combination_structure(self):
        """Test EN-DC combination structure."""
        combo = ENDC_COMBINATIONS["DC_2A_n41A"]
        assert "lte" in combo
        assert "nr" in combo
        assert "max_bw" in combo
        assert combo["lte"] == ["B2"]
        assert combo["nr"] == ["n41"]

    def test_endc_multi_carrier_combinations(self):
        """Test EN-DC with multiple carriers."""
        # Multiple LTE + single NR
        combo = ENDC_COMBINATIONS["DC_2A-66A_n41A"]
        assert len(combo["lte"]) == 2
        assert len(combo["nr"]) == 1

        # Single LTE + multiple NR
        combo = ENDC_COMBINATIONS["DC_2A_n41C"]
        assert len(combo["lte"]) == 1
        assert len(combo["nr"]) == 2


# ══════════════════════════════════════════════════════════════
# TEST: EARFCN/ARFCN MAPPINGS
# ══════════════════════════════════════════════════════════════

class TestFrequencyMappings:
    """Test EARFCN/ARFCN frequency mappings."""

    def test_lte_earfcn_map_coverage(self):
        """Test LTE EARFCN map has common bands."""
        common_bands = ["B2", "B4", "B5", "B12", "B13", "B66", "B71"]
        for band in common_bands:
            assert band in LTE_EARFCN_MAP, f"Missing EARFCN for {band}"
            assert LTE_EARFCN_MAP[band] > 0

    def test_nr_arfcn_map_coverage(self):
        """Test NR ARFCN map has common bands."""
        common_bands = ["n2", "n5", "n41", "n66", "n71", "n77", "n78", "n257"]
        for band in common_bands:
            assert band in NR_ARFCN_MAP, f"Missing ARFCN for {band}"
            assert NR_ARFCN_MAP[band] > 0

    def test_get_earfcn(self):
        """Test get_earfcn function."""
        assert get_earfcn("B2") == 900
        assert get_earfcn("B41") == 40620
        assert get_earfcn("unknown") == 0  # Unknown band

    def test_get_arfcn(self):
        """Test get_arfcn function."""
        assert get_arfcn("n41") == 520000
        assert get_arfcn("n257") == 2079167
        assert get_arfcn("unknown") == 0  # Unknown band

    def test_default_bandwidth_coverage(self):
        """Test default bandwidth map has all bands."""
        # LTE bands
        for band in LTE_EARFCN_MAP.keys():
            assert band in DEFAULT_BANDWIDTH, f"Missing default BW for {band}"

        # NR bands
        for band in NR_ARFCN_MAP.keys():
            assert band in DEFAULT_BANDWIDTH, f"Missing default BW for {band}"

    def test_get_default_bandwidth(self):
        """Test get_default_bandwidth function."""
        assert get_default_bandwidth("B2") == 20
        assert get_default_bandwidth("n41") == 100
        assert get_default_bandwidth("n257") == 400  # FR2
        assert get_default_bandwidth("unknown") == 20  # Default


# ══════════════════════════════════════════════════════════════
# TEST: CARRIER CONFIG
# ══════════════════════════════════════════════════════════════

class TestCarrierConfig:
    """Test CarrierConfig dataclass."""

    def test_carrier_config_creation(self):
        """Test creating a CarrierConfig."""
        config = CarrierConfig(
            band="B2",
            bandwidth_mhz=20,
            role=CellRole.PCELL,
            earfcn=900,
            cell_id=1,
            pci=1,
            rat="lte",
        )
        assert config.band == "B2"
        assert config.bandwidth_mhz == 20
        assert config.role == CellRole.PCELL
        assert config.rat == "lte"

    def test_carrier_config_defaults(self):
        """Test CarrierConfig default values."""
        config = CarrierConfig(
            band="n41",
            bandwidth_mhz=100,
            role=CellRole.SCELL,
        )
        assert config.earfcn is None
        assert config.arfcn is None
        assert config.cell_id == 0
        assert config.n_antenna_dl == 2
        assert config.dl_mcs is None


# ══════════════════════════════════════════════════════════════
# TEST: CA CONFIGURATION
# ══════════════════════════════════════════════════════════════

class TestCAConfiguration:
    """Test CAConfiguration dataclass."""

    def test_ca_config_creation(self):
        """Test creating a CAConfiguration."""
        carriers = [
            CarrierConfig(band="B2", bandwidth_mhz=20, role=CellRole.PCELL, rat="lte"),
            CarrierConfig(band="B4", bandwidth_mhz=20, role=CellRole.SCELL, rat="lte"),
        ]
        config = CAConfiguration(
            name="CA_2A-4A",
            ca_type=CAType.LTE_CA,
            band_type=CABandType.INTER_BAND,
            carriers=carriers,
        )
        assert config.name == "CA_2A-4A"
        assert config.num_carriers == 2
        assert config.total_bandwidth_mhz == 40

    def test_ca_config_throughput_calculation(self):
        """Test automatic throughput calculation."""
        carriers = [
            CarrierConfig(band="B2", bandwidth_mhz=20, role=CellRole.PCELL, rat="lte"),
            CarrierConfig(band="B4", bandwidth_mhz=20, role=CellRole.SCELL, rat="lte"),
        ]
        config = CAConfiguration(
            name="CA_2A-4A",
            ca_type=CAType.LTE_CA,
            band_type=CABandType.INTER_BAND,
            carriers=carriers,
        )
        # LTE: ~3.75 Mbps per MHz for DL
        assert config.expected_dl_mbps > 0
        assert config.expected_ul_mbps > 0

    def test_ca_config_pcell_property(self):
        """Test pcell property."""
        carriers = [
            CarrierConfig(band="B2", bandwidth_mhz=20, role=CellRole.PCELL, rat="lte"),
            CarrierConfig(band="B4", bandwidth_mhz=20, role=CellRole.SCELL, rat="lte"),
        ]
        config = CAConfiguration(
            name="CA_2A-4A",
            ca_type=CAType.LTE_CA,
            band_type=CABandType.INTER_BAND,
            carriers=carriers,
        )
        pcell = config.pcell
        assert pcell is not None
        assert pcell.band == "B2"
        assert pcell.role == CellRole.PCELL

    def test_ca_config_scells_property(self):
        """Test scells property."""
        carriers = [
            CarrierConfig(band="B2", bandwidth_mhz=20, role=CellRole.PCELL, rat="lte"),
            CarrierConfig(band="B4", bandwidth_mhz=20, role=CellRole.SCELL, rat="lte"),
            CarrierConfig(band="B12", bandwidth_mhz=10, role=CellRole.SCELL, rat="lte"),
        ]
        config = CAConfiguration(
            name="CA_2A-4A-12A",
            ca_type=CAType.LTE_CA,
            band_type=CABandType.INTER_BAND,
            carriers=carriers,
        )
        scells = config.scells
        assert len(scells) == 2
        assert all(c.role == CellRole.SCELL for c in scells)


# ══════════════════════════════════════════════════════════════
# TEST: SCENARIO BUILDERS
# ══════════════════════════════════════════════════════════════

class TestScenarioBuilders:
    """Test CA scenario builder functions."""

    def test_create_lte_ca_config(self):
        """Test create_lte_ca_config function."""
        config = create_lte_ca_config(
            name="CA_2A-4A",
            bands=["B2", "B4"],
            band_type=CABandType.INTER_BAND,
        )
        assert config.ca_type == CAType.LTE_CA
        assert config.num_carriers == 2
        assert config.carriers[0].role == CellRole.PCELL
        assert config.carriers[1].role == CellRole.SCELL
        assert all(c.rat == "lte" for c in config.carriers)

    def test_create_nr_ca_config(self):
        """Test create_nr_ca_config function."""
        config = create_nr_ca_config(
            name="CA_n2A-n66A",
            bands=["n2", "n66"],
            band_type=CABandType.INTER_BAND,
        )
        assert config.ca_type == CAType.NR_CA
        assert config.num_carriers == 2
        assert all(c.rat == "nr" for c in config.carriers)

    def test_create_endc_config(self):
        """Test create_endc_config function."""
        config = create_endc_config(
            name="DC_2A_n41A",
            lte_bands=["B2"],
            nr_bands=["n41"],
        )
        assert config.ca_type == CAType.ENDC
        assert config.num_carriers == 2

        # Check LTE carrier
        lte_carriers = [c for c in config.carriers if c.rat == "lte"]
        assert len(lte_carriers) == 1
        assert lte_carriers[0].role == CellRole.PCELL

        # Check NR carrier
        nr_carriers = [c for c in config.carriers if c.rat == "nr"]
        assert len(nr_carriers) == 1
        assert nr_carriers[0].role == CellRole.PSCELL  # Primary SCell in EN-DC

    def test_create_endc_config_multi_carrier(self):
        """Test create_endc_config with multiple carriers."""
        config = create_endc_config(
            name="DC_2A-66A_n41A",
            lte_bands=["B2", "B66"],
            nr_bands=["n41"],
        )
        assert config.num_carriers == 3

        lte_carriers = [c for c in config.carriers if c.rat == "lte"]
        assert len(lte_carriers) == 2
        assert lte_carriers[0].role == CellRole.PCELL
        assert lte_carriers[1].role == CellRole.SCELL


# ══════════════════════════════════════════════════════════════
# TEST: TEST SCENARIOS
# ══════════════════════════════════════════════════════════════

class TestCATestScenarios:
    """Test pre-defined CA test scenarios."""

    def test_scenarios_generated(self):
        """Test that scenarios are generated from combinations."""
        assert len(CA_TEST_SCENARIOS) > 0

        # Count by type
        lte_count = sum(1 for cfg in CA_TEST_SCENARIOS.values()
                       if cfg.ca_type == CAType.LTE_CA)
        nr_count = sum(1 for cfg in CA_TEST_SCENARIOS.values()
                      if cfg.ca_type == CAType.NR_CA)
        endc_count = sum(1 for cfg in CA_TEST_SCENARIOS.values()
                        if cfg.ca_type == CAType.ENDC)

        assert lte_count == len(LTE_CA_COMBINATIONS)
        assert nr_count == len(NR_CA_COMBINATIONS)
        assert endc_count == len(ENDC_COMBINATIONS)

    def test_lte_ca_scenario_naming(self):
        """Test LTE CA scenario naming convention."""
        # Check a known scenario
        assert "lte_ca_2a_4a" in CA_TEST_SCENARIOS
        config = CA_TEST_SCENARIOS["lte_ca_2a_4a"]
        assert config.ca_type == CAType.LTE_CA
        assert "B2" in [c.band for c in config.carriers]
        assert "B4" in [c.band for c in config.carriers]

    def test_nr_ca_scenario_naming(self):
        """Test NR CA scenario naming convention."""
        assert "nr_ca_n2a_n66a" in CA_TEST_SCENARIOS
        config = CA_TEST_SCENARIOS["nr_ca_n2a_n66a"]
        assert config.ca_type == CAType.NR_CA

    def test_endc_scenario_naming(self):
        """Test EN-DC scenario naming convention."""
        assert "endc_2a_n41a" in CA_TEST_SCENARIOS
        config = CA_TEST_SCENARIOS["endc_2a_n41a"]
        assert config.ca_type == CAType.ENDC

    def test_all_scenarios_have_valid_config(self):
        """Test all scenarios have valid configuration."""
        for name, config in CA_TEST_SCENARIOS.items():
            assert config.name, f"Scenario {name} missing name"
            assert config.num_carriers > 0, f"Scenario {name} has no carriers"
            assert config.total_bandwidth_mhz > 0, f"Scenario {name} has no bandwidth"
            assert config.expected_dl_mbps > 0, f"Scenario {name} has no expected DL"
            assert config.expected_ul_mbps > 0, f"Scenario {name} has no expected UL"


# ══════════════════════════════════════════════════════════════
# TEST: CARRIER RESULT
# ══════════════════════════════════════════════════════════════

class TestCarrierResult:
    """Test CarrierResult dataclass."""

    def test_carrier_result_creation(self):
        """Test creating a CarrierResult."""
        result = CarrierResult(
            band="B2",
            role="pcell",
            rat="lte",
            bandwidth_mhz=20,
            dl_avg_mbps=65.0,
            dl_max_mbps=72.0,
            ul_avg_mbps=45.0,
            ul_max_mbps=50.0,
            active=True,
        )
        assert result.band == "B2"
        assert result.active is True

    def test_carrier_result_defaults(self):
        """Test CarrierResult default values."""
        result = CarrierResult(
            band="B4",
            role="scell",
            rat="lte",
            bandwidth_mhz=20,
            dl_avg_mbps=0.0,
            dl_max_mbps=0.0,
            ul_avg_mbps=0.0,
            ul_max_mbps=0.0,
        )
        assert result.active is True  # Default


# ══════════════════════════════════════════════════════════════
# TEST: CA TEST RESULT
# ══════════════════════════════════════════════════════════════

class TestCATestResult:
    """Test CATestResult dataclass."""

    def test_ca_result_creation(self):
        """Test creating a CATestResult."""
        result = CATestResult(
            scenario_name="CA_2A-4A",
            ca_type="lte_ca",
            band_type="inter_band",
            num_carriers=2,
            total_bandwidth_mhz=40,
            dl_agg_avg_mbps=130.0,
            dl_agg_max_mbps=145.0,
            ul_agg_avg_mbps=90.0,
            ul_agg_max_mbps=100.0,
            expected_dl_mbps=150.0,
            expected_ul_mbps=100.0,
            dl_efficiency=86.7,
            ul_efficiency=90.0,
            active_carrier_count=2,
            all_scells_active=True,
            passed=True,
        )
        assert result.passed is True
        assert result.active_carrier_count == 2

    def test_ca_result_to_dict(self):
        """Test CATestResult to_dict method."""
        carrier_results = [
            CarrierResult(
                band="B2", role="pcell", rat="lte", bandwidth_mhz=20,
                dl_avg_mbps=65.0, dl_max_mbps=72.0,
                ul_avg_mbps=45.0, ul_max_mbps=50.0,
            ),
        ]
        result = CATestResult(
            scenario_name="CA_2A-4A",
            ca_type="lte_ca",
            band_type="inter_band",
            num_carriers=2,
            total_bandwidth_mhz=40,
            carrier_results=carrier_results,
        )
        result_dict = result.to_dict()

        assert "scenario_name" in result_dict
        assert "carrier_results" in result_dict
        assert isinstance(result_dict["carrier_results"], list)
        assert result_dict["carrier_results"][0]["band"] == "B2"

    def test_ca_result_defaults(self):
        """Test CATestResult default values."""
        result = CATestResult(
            scenario_name="test",
            ca_type="lte_ca",
            band_type="inter_band",
            num_carriers=2,
            total_bandwidth_mhz=40,
        )
        assert result.carrier_results == []
        assert result.dl_agg_avg_mbps == 0.0
        assert result.scell_activation_time_ms == 0.0
        assert result.passed is False


# ══════════════════════════════════════════════════════════════
# TEST: CA TEST SUITE (Unit)
# ══════════════════════════════════════════════════════════════

class TestCATestSuiteUnit:
    """Unit tests for CATestSuite (no live callbox required)."""

    def test_suite_creation(self):
        """Test creating CATestSuite."""
        suite = CATestSuite(host="127.0.0.1")
        assert suite.host == "127.0.0.1"
        assert suite.cb is None
        assert suite.results == []

    def test_suite_with_options(self):
        """Test CATestSuite with all options."""
        suite = CATestSuite(
            host="192.168.1.80",
            password="secret",
            ssl=True,
            ssl_verify=True,
        )
        assert suite.host == "192.168.1.80"
        assert suite.password == "secret"
        assert suite.ssl is True
        assert suite.ssl_verify is True


# ══════════════════════════════════════════════════════════════
# TEST: CA TEST SUITE (Live)
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def live_host(request):
    """Get live host from pytest command line."""
    host = request.config.getoption("--host", default=None)
    if not host:
        pytest.skip("No --host provided for live tests")
    return host


class TestCATestSuiteLive:
    """Live integration tests for CATestSuite (requires callbox)."""

    @pytest.fixture
    def suite(self, live_host):
        """Create and connect test suite."""
        suite = CATestSuite(host=live_host)
        if suite.connect():
            yield suite
            suite.disconnect()
        else:
            pytest.skip("Could not connect to Callbox")

    def test_connect_disconnect(self, live_host):
        """Test connecting and disconnecting."""
        suite = CATestSuite(host=live_host)
        connected = suite.connect()
        if connected:
            assert suite.cb is not None
            suite.disconnect()
            assert suite.cb is None

    def test_get_cell_stats(self, suite):
        """Test getting cell statistics."""
        stats = suite.get_cell_stats()
        assert isinstance(stats, dict)

    def test_get_ue_info(self, suite):
        """Test getting UE information."""
        ue_list = suite.get_ue_info()
        assert isinstance(ue_list, list)

    def test_run_single_test(self, suite):
        """Test running a single CA test."""
        config = CA_TEST_SCENARIOS.get("lte_ca_2a_4a")
        if config:
            result = suite.run_test(config, duration=10)
            assert isinstance(result, CATestResult)
            assert result.scenario_name == config.name


# ══════════════════════════════════════════════════════════════
# TEST: REPORTING
# ══════════════════════════════════════════════════════════════

class TestReporting:
    """Test result reporting functionality."""

    @pytest.fixture
    def suite_with_results(self):
        """Create suite with mock results."""
        suite = CATestSuite(host="127.0.0.1")
        suite.results = [
            CATestResult(
                scenario_name="CA_2A-4A",
                ca_type="lte_ca",
                band_type="inter_band",
                num_carriers=2,
                total_bandwidth_mhz=40,
                dl_agg_avg_mbps=130.0,
                dl_agg_max_mbps=145.0,
                ul_agg_avg_mbps=90.0,
                ul_agg_max_mbps=100.0,
                expected_dl_mbps=150.0,
                expected_ul_mbps=100.0,
                dl_efficiency=86.7,
                ul_efficiency=90.0,
                active_carrier_count=2,
                passed=True,
            ),
            CATestResult(
                scenario_name="CA_2A-66A",
                ca_type="lte_ca",
                band_type="inter_band",
                num_carriers=2,
                total_bandwidth_mhz=40,
                dl_agg_avg_mbps=125.0,
                dl_agg_max_mbps=140.0,
                ul_agg_avg_mbps=85.0,
                ul_agg_max_mbps=95.0,
                expected_dl_mbps=150.0,
                expected_ul_mbps=100.0,
                dl_efficiency=83.3,
                ul_efficiency=85.0,
                active_carrier_count=2,
                passed=True,
            ),
        ]
        return suite

    def test_print_summary(self, suite_with_results, capsys):
        """Test print_summary output."""
        suite_with_results.print_summary()
        captured = capsys.readouterr()

        assert "CA TEST SUMMARY" in captured.out
        assert "CA_2A-4A" in captured.out
        assert "CA_2A-66A" in captured.out
        assert "PASS" in captured.out

    def test_export_results(self, suite_with_results, tmp_path):
        """Test exporting results to JSON."""
        output_file = tmp_path / "ca_results.json"
        suite_with_results.export_results(str(output_file))

        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert data["test_suite"] == "CA Test Suite"
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["summary"]["total_tests"] == 2
        assert data["summary"]["passed"] == 2

    def test_export_results_content(self, suite_with_results, tmp_path):
        """Test exported result content."""
        output_file = tmp_path / "ca_results.json"
        suite_with_results.export_results(str(output_file))

        with open(output_file) as f:
            data = json.load(f)

        result = data["results"][0]
        assert "scenario_name" in result
        assert "ca_type" in result
        assert "num_carriers" in result
        assert "dl_agg_avg_mbps" in result
        assert "carrier_results" in result


# ══════════════════════════════════════════════════════════════
# TEST: CA TYPE SPECIFIC THROUGHPUT CALCULATIONS
# ══════════════════════════════════════════════════════════════

class TestThroughputCalculations:
    """Test throughput calculation logic."""

    def test_lte_ca_throughput(self):
        """Test LTE CA throughput calculation."""
        config = create_lte_ca_config(
            name="Test_CA",
            bands=["B2", "B4"],  # 20+20 = 40 MHz
            band_type=CABandType.INTER_BAND,
        )
        # LTE: ~3.75 Mbps per MHz for DL
        assert 140 <= config.expected_dl_mbps <= 160

    def test_nr_ca_throughput(self):
        """Test NR CA throughput calculation."""
        config = create_nr_ca_config(
            name="Test_CA",
            bands=["n41", "n41"],  # 100+100 = 200 MHz
            band_type=CABandType.INTRA_BAND_CONTIGUOUS,
        )
        # NR FR1: ~5 Mbps per MHz for DL
        assert config.expected_dl_mbps >= 500

    def test_endc_throughput(self):
        """Test EN-DC throughput calculation."""
        config = create_endc_config(
            name="Test_DC",
            lte_bands=["B2"],   # 20 MHz LTE
            nr_bands=["n41"],   # 100 MHz NR
        )
        # Combined LTE + NR throughput
        assert config.expected_dl_mbps > 0
        # Should be higher than LTE-only
        lte_only = create_lte_ca_config("LTE", ["B2"], CABandType.INTER_BAND)
        assert config.expected_dl_mbps > lte_only.expected_dl_mbps


# ══════════════════════════════════════════════════════════════
# TEST: EDGE CASES
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_band_earfcn(self):
        """Test handling unknown band for EARFCN."""
        assert get_earfcn("B999") == 0

    def test_unknown_band_arfcn(self):
        """Test handling unknown band for ARFCN."""
        assert get_arfcn("n999") == 0

    def test_empty_carrier_list(self):
        """Test CAConfiguration with empty carrier list."""
        config = CAConfiguration(
            name="Empty",
            ca_type=CAType.LTE_CA,
            band_type=CABandType.INTER_BAND,
            carriers=[],
        )
        assert config.num_carriers == 0
        assert config.total_bandwidth_mhz == 0
        assert config.pcell is None

    def test_single_carrier_config(self):
        """Test CAConfiguration with single carrier."""
        carriers = [
            CarrierConfig(band="B2", bandwidth_mhz=20, role=CellRole.PCELL, rat="lte"),
        ]
        config = CAConfiguration(
            name="Single",
            ca_type=CAType.LTE_CA,
            band_type=CABandType.INTER_BAND,
            carriers=carriers,
        )
        assert config.num_carriers == 1
        assert len(config.scells) == 0
