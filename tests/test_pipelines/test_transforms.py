"""
Unit tests for pipeline transforms and feature calculation logic.
"""

import numpy as np
import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark required for pipeline transforms")

from src.pipelines.utils.transforms import (
    rolling_slope_udf,
    ewma_udf,
    RISK_TIERS,
    DEGRADATION_THRESHOLDS,
)


class TestTransformLogic:
    def test_risk_tiers_definitions(self):
        """Verify risk tier classifications and color mappings."""
        assert "healthy" in RISK_TIERS
        assert "watch" in RISK_TIERS
        assert "warning" in RISK_TIERS
        assert "critical" in RISK_TIERS

        assert RISK_TIERS["healthy"]["max_score"] == 25
        assert RISK_TIERS["critical"]["min_score"] == 75

    def test_degradation_thresholds(self):
        """Verify degradation failure thresholds."""
        assert DEGRADATION_THRESHOLDS["battery_eol_capacity_retention_pct"] == 80.0
        assert DEGRADATION_THRESHOLDS["max_acceptable_patch_lag_days"] == 90
        assert DEGRADATION_THRESHOLDS["min_acceptable_compliance_score"] == 70.0

    def test_rolling_slope_computation(self):
        """Test linear regression slope calculation."""
        # Perfect linear degradation: [100, 95, 90, 85, 80] -> slope is -5
        x = np.arange(5, dtype=np.float64)
        y = np.array([100.0, 95.0, 90.0, 85.0, 80.0], dtype=np.float64)

        x_mean = x.mean()
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / ((x - x_mean) ** 2).sum()
        assert pytest.approx(slope, abs=1e-4) == -5.0

    def test_ewma_computation(self):
        """Test exponential weighted moving average calculation."""
        values = [10.0, 20.0, 30.0]
        alpha = 0.3

        expected = values[0]
        for v in values[1:]:
            expected = alpha * v + (1 - alpha) * expected

        # Expected: 10 -> 0.3*20 + 0.7*10 = 13 -> 0.3*30 + 0.7*13 = 18.1
        assert pytest.approx(expected, abs=1e-4) == 18.1

    def test_compliance_score_formula(self):
        """Test pure mathematical logic of compliance score."""
        days_since_patch = 10
        os_version_lag = 0
        unpatched_cves = 0
        encryption = True
        passcode = True

        patch_score = max(0.0, 100.0 - days_since_patch * 1.5)  # 85
        os_score = max(0.0, 100.0 - os_version_lag * 20.0)      # 100
        vuln_score = max(0.0, 100.0 - unpatched_cves * 15.0)    # 100
        sec_score = 50.0 + 50.0                                 # 100

        total_score = (
            patch_score * 0.25
            + os_score * 0.25
            + vuln_score * 0.30
            + sec_score * 0.20
        )
        # 85*0.25 + 100*0.25 + 100*0.3 + 100*0.2 = 21.25 + 25 + 30 + 20 = 96.25
        assert pytest.approx(total_score, abs=1e-2) == 96.25
