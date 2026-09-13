"""
FleetPulse — Model Serving Endpoint Handler
=============================================
Compatible with Databricks Model Serving.
Accepts device features as JSON, returns RUL prediction + anomaly flag +
risk score + driving factors.

This module can be deployed as:
1. A Databricks Model Serving endpoint (via MLflow model registry)
2. A standalone FastAPI endpoint for local development

Input schema:
    {
        "device_id": "DEV-ABC12345",
        "features": {
            "cycle_count": 150,
            "current_capacity_ah": 1.65,
            "nominal_capacity_ah": 2.0,
            ...
        }
    }

Output schema:
    {
        "device_id": "DEV-ABC12345",
        "remaining_useful_life_days": 42.5,
        "days_to_non_compliance": 15.0,
        "anomaly_flag": false,
        "anomaly_score": -0.15,
        "risk_score": 65.3,
        "risk_tier": "warning",
        "driving_factors": [
            {"factor": "capacity_fade_rate", "importance": 0.35, "value": -0.008},
            {"factor": "days_since_last_patch", "importance": 0.22, "value": 45},
        ]
    }
"""

import json
from typing import Any

try:
    import mlflow
except ImportError:
    mlflow = None

import pandas as pd


class FleetPulsePredictor:
    """
    Unified prediction handler that wraps both the RUL regressor
    and Isolation Forest anomaly detector.
    """

    FEATURE_COLUMNS = [
        "cycle_count",
        "current_capacity_ah",
        "nominal_capacity_ah",
        "capacity_fade_pct",
        "capacity_fade_rate",
        "avg_temperature_exposure_c",
        "max_temperature_c",
        "voltage_drop_rate",
        "internal_resistance_trend",
        "days_since_last_patch",
        "os_version_lag",
        "unpatched_critical_cves",
        "compliance_score",
        "battery_health_score",
        "overall_risk_score",
    ]

    def __init__(
        self,
        rul_model_uri: str | None = None,
        anomaly_model_uri: str | None = None,
        rul_model: Any = None,
        anomaly_model: Any = None,
        anomaly_scaler: Any = None,
    ):
        """
        Initialize with MLflow model URIs or pre-loaded models.

        For Databricks Model Serving, models are loaded via URI.
        For local dev, models can be passed directly.
        """
        if rul_model_uri:
            self.rul_model = mlflow.pyfunc.load_model(rul_model_uri)
        else:
            self.rul_model = rul_model

        if anomaly_model_uri:
            self.anomaly_model = mlflow.pyfunc.load_model(anomaly_model_uri)
        else:
            self.anomaly_model = anomaly_model

        self.anomaly_scaler = anomaly_scaler

        # Load feature importance for driving factors
        self._feature_importance = {}
        self._load_feature_importance(rul_model_uri)

    def _load_feature_importance(self, model_uri: str | None):
        """Try to load feature importance from the model's MLflow run."""
        if model_uri and model_uri.startswith("runs:/"):
            try:
                run_id = model_uri.split("/")[1]
                client = mlflow.tracking.MlflowClient()
                artifact_path = client.download_artifacts(run_id, "feature_importance.json")
                with open(artifact_path) as f:
                    self._feature_importance = json.load(f)
            except Exception:
                pass

    def predict(self, input_data: dict | list[dict]) -> dict | list[dict]:
        """
        Run prediction for one or more devices.

        Args:
            input_data: Single device dict or list of device dicts.
                Each dict should have "device_id" and "features" keys.

        Returns:
            Prediction result(s) with RUL, anomaly flag, risk info, and driving factors.
        """
        if isinstance(input_data, dict):
            return self._predict_single(input_data)
        return [self._predict_single(d) for d in input_data]

    def _predict_single(self, device_data: dict) -> dict:
        """Predict for a single device."""
        device_id = device_data.get("device_id", "unknown")
        features = device_data.get("features", device_data)

        # Build feature vector
        feature_values = {}
        for col in self.FEATURE_COLUMNS:
            feature_values[col] = features.get(col, 0.0)

        X = pd.DataFrame([feature_values])

        # ── RUL Prediction ───────────────────────────────────────────────
        rul_days = None
        compliance_days = None

        if self.rul_model is not None:
            try:
                pred = self.rul_model.predict(X)
                if hasattr(pred, '__len__'):
                    rul_days = float(pred[0])
                else:
                    rul_days = float(pred)
            except Exception as e:
                print(f"RUL prediction error: {e}")

        # ── Anomaly Detection ────────────────────────────────────────────
        anomaly_flag = False
        anomaly_score = 0.0

        if self.anomaly_model is not None:
            try:
                X_scaled = X.copy()
                if self.anomaly_scaler is not None:
                    X_scaled = pd.DataFrame(
                        self.anomaly_scaler.transform(X),
                        columns=self.FEATURE_COLUMNS,
                    )

                if hasattr(self.anomaly_model, "predict"):
                    anomaly_pred = self.anomaly_model.predict(X_scaled)
                    anomaly_flag = bool(anomaly_pred[0] == -1)
                    anomaly_score = float(self.anomaly_model.decision_function(X_scaled)[0])
                else:
                    # MLflow pyfunc wrapper
                    anomaly_pred = self.anomaly_model.predict(X_scaled)
                    anomaly_flag = bool(anomaly_pred[0] == -1) if hasattr(anomaly_pred, '__len__') else False
            except Exception as e:
                print(f"Anomaly detection error: {e}")

        # ── Risk Assessment ──────────────────────────────────────────────
        risk_score = features.get("overall_risk_score", 50.0)
        if rul_days is not None and rul_days < 30:
            risk_score = max(risk_score, 75.0)  # Boost risk for low RUL
        if anomaly_flag:
            risk_score = max(risk_score, 80.0)  # Boost risk for anomalies

        risk_tier = (
            "healthy" if risk_score <= 25
            else "watch" if risk_score <= 50
            else "warning" if risk_score <= 75
            else "critical"
        )

        # ── Driving Factors ──────────────────────────────────────────────
        driving_factors = []
        importance = self._feature_importance or self._compute_naive_importance(features)

        for factor, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]:
            driving_factors.append({
                "factor": factor,
                "importance": round(float(imp), 4),
                "value": features.get(factor, 0.0),
                "description": self._get_factor_description(factor, features.get(factor, 0.0)),
            })

        return {
            "device_id": device_id,
            "remaining_useful_life_days": round(rul_days, 1) if rul_days is not None else None,
            "days_to_non_compliance": round(compliance_days, 1) if compliance_days is not None else None,
            "anomaly_flag": anomaly_flag,
            "anomaly_score": round(anomaly_score, 4),
            "risk_score": round(float(risk_score), 1),
            "risk_tier": risk_tier,
            "driving_factors": driving_factors,
        }

    @staticmethod
    def _compute_naive_importance(features: dict) -> dict:
        """Fallback feature importance based on value deviation from healthy baselines."""
        baselines = {
            "capacity_fade_pct": (0, 30, True),       # (healthy, critical, higher_is_worse)
            "capacity_fade_rate": (0, -0.01, False),
            "days_since_last_patch": (0, 90, True),
            "os_version_lag": (0, 3, True),
            "unpatched_critical_cves": (0, 5, True),
            "overall_risk_score": (0, 100, True),
            "cycle_count": (0, 500, True),
            "avg_temperature_exposure_c": (25, 50, True),
        }
        importance = {}
        for feat, (healthy, critical, higher_worse) in baselines.items():
            val = features.get(feat, healthy)
            if critical != healthy:
                deviation = abs(val - healthy) / abs(critical - healthy)
            else:
                deviation = 0
            importance[feat] = min(deviation, 1.0)
        return importance

    @staticmethod
    def _get_factor_description(factor: str, value: float) -> str:
        """Human-readable description of a risk factor."""
        descriptions = {
            "capacity_fade_pct": f"Battery has lost {value:.1f}% of original capacity",
            "capacity_fade_rate": f"Battery capacity declining at {abs(value):.4f} Ah/cycle",
            "days_since_last_patch": f"Last security patch was {int(value)} days ago",
            "os_version_lag": f"OS is {int(value)} version(s) behind latest",
            "unpatched_critical_cves": f"{int(value)} unpatched critical vulnerabilities",
            "cycle_count": f"Battery has completed {int(value)} charge cycles",
            "avg_temperature_exposure_c": f"Average operating temperature: {value:.1f}°C",
            "voltage_drop_rate": f"End-of-discharge voltage declining at {abs(value):.4f} V/cycle",
            "internal_resistance_trend": f"Internal resistance growing at {value:.4f} Ω/cycle",
            "overall_risk_score": f"Overall risk score: {value:.1f}/100",
            "compliance_score": f"Compliance score: {value:.1f}/100",
            "battery_health_score": f"Battery health score: {value:.1f}/100",
        }
        return descriptions.get(factor, f"{factor}: {value}")


# ==============================================================================
_BaseModel = mlflow.pyfunc.PythonModel if mlflow is not None else object


class FleetPulseMLflowWrapper(_BaseModel):
    """
    MLflow PythonModel wrapper for Databricks Model Serving deployment.

    Wraps both RUL and anomaly models into a single serving endpoint.
    """

    def load_context(self, context):
        """Load models from MLflow artifacts."""
        artifacts = context.artifacts

        self.predictor = FleetPulsePredictor(
            rul_model_uri=artifacts.get("rul_model"),
            anomaly_model_uri=artifacts.get("anomaly_model"),
        )

    def predict(self, context, model_input):
        """
        Predict for a batch of devices.

        model_input: pd.DataFrame with device feature columns
        """
        results = []
        for _, row in model_input.iterrows():
            device_data = {
                "device_id": row.get("device_id", "unknown"),
                "features": row.to_dict(),
            }
            results.append(self.predictor.predict(device_data))
        return pd.DataFrame(results)
