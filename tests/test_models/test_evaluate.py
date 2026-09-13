"""
Unit tests for model prediction, serving handler, and evaluation metrics.
"""

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.models.serve.predict import FleetPulsePredictor


class TestModelPredictionAndEvaluation:
    def test_metrics_computation(self):
        """Verify standard regression evaluation metrics."""
        y_true = np.array([50.0, 30.0, 15.0, 5.0, 80.0])
        y_pred = np.array([48.0, 33.0, 12.0, 7.0, 78.0])

        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)

        assert mae < 3.0
        assert rmse < 3.0
        assert r2 > 0.95

    def test_predictor_single_device_inference(self):
        """Verify serving predictor produces expected output schema and risk calculations."""
        predictor = FleetPulsePredictor()

        payload = {
            "device_id": "DEV-TEST-001",
            "features": {
                "cycle_count": 250,
                "current_capacity_ah": 1.6,
                "nominal_capacity_ah": 2.0,
                "capacity_fade_pct": 20.0,
                "capacity_fade_rate": -0.005,
                "avg_temperature_exposure_c": 32.0,
                "voltage_drop_rate": -0.01,
                "internal_resistance_ohm": 0.12,
                "days_since_last_patch": 45,
                "os_version_lag": 1,
                "unpatched_cve_count": 2,
                "device_encrypted": 1,
                "passcode_enforced": 1,
            }
        }

        result = predictor.predict(payload)

        assert result["device_id"] == "DEV-TEST-001"
        assert "remaining_useful_life_days" in result
        assert "days_to_non_compliance" in result
        assert "risk_score" in result
        assert "risk_tier" in result
        assert result["risk_tier"] in ["healthy", "watch", "warning", "critical"]
        assert isinstance(result["driving_factors"], list)
        assert len(result["driving_factors"]) > 0

    def test_predictor_batch_inference(self):
        """Verify batch prediction handling."""
        predictor = FleetPulsePredictor()

        records = [
            {
                "device_id": f"DEV-BATCH-{i}",
                "features": {
                    "cycle_count": 100 * i,
                    "current_capacity_ah": 2.0 - (0.2 * i),
                    "nominal_capacity_ah": 2.0,
                    "capacity_fade_pct": 10.0 * i,
                    "capacity_fade_rate": -0.003 * i,
                    "avg_temperature_exposure_c": 28.0 + i,
                    "voltage_drop_rate": -0.005 * i,
                    "internal_resistance_ohm": 0.10 + 0.02 * i,
                    "days_since_last_patch": 15 * i,
                    "os_version_lag": i,
                    "unpatched_cve_count": i,
                    "overall_risk_score": 25.0 * i,
                    "device_encrypted": 1,
                    "passcode_enforced": 1,
                }
            }
            for i in range(1, 4)
        ]

        results = predictor.predict(records)
        assert len(results) == 3
        # Higher cycle count and patch lag should produce higher risk score
        assert results[2]["risk_score"] > results[0]["risk_score"]
