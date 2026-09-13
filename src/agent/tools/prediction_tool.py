"""
FleetPulse — Prediction Tool
==============================
Agent tool that calls the Model Serving endpoint (or local model)
for fleet-level and device-level predictions.
"""

import os
from typing import Any

import httpx
import pandas as pd


class PredictionTool:
    """
    Wraps the FleetPulse prediction model for use as an agent tool.
    Supports both Databricks Model Serving and local model inference.
    """

    def __init__(
        self,
        serving_endpoint: str | None = None,
        databricks_host: str | None = None,
        databricks_token: str | None = None,
        local_predictor: Any = None,
        feature_data: pd.DataFrame | None = None,
    ):
        """
        Args:
            serving_endpoint: Databricks Model Serving endpoint name
            databricks_host: Databricks workspace URL
            databricks_token: Databricks personal access token
            local_predictor: FleetPulsePredictor instance for local mode
            feature_data: Pre-loaded feature DataFrame for local mode
        """
        self.serving_endpoint = serving_endpoint or os.getenv("MODEL_SERVING_ENDPOINT")
        self.databricks_host = databricks_host or os.getenv("DATABRICKS_HOST", "")
        self.databricks_token = databricks_token or os.getenv("DATABRICKS_TOKEN", "")
        self.local_predictor = local_predictor
        self._feature_data = feature_data

    def _load_feature_data(self) -> pd.DataFrame:
        """Load or return cached feature data."""
        if self._feature_data is not None:
            return self._feature_data

        # Try loading from local processed data
        local_paths = [
            "data/processed/device_health/",
            "data/processed/device_health.parquet",
            "data/processed/device_health.csv",
        ]
        for path in local_paths:
            try:
                if path.endswith(".csv"):
                    self._feature_data = pd.read_csv(path)
                else:
                    self._feature_data = pd.read_parquet(path)
                return self._feature_data
            except (FileNotFoundError, Exception):
                continue

        # Generate synthetic feature data as fallback
        self._feature_data = self._generate_synthetic_features()
        return self._feature_data

    def _generate_synthetic_features(self) -> pd.DataFrame:
        """Generate synthetic feature data for development/demo."""
        import numpy as np

        np.random.seed(42)

        devices = []
        fleet_names = ["Sales", "Engineering", "Executive", "Support", "Marketing", "Operations"]
        device_models = [
            "iPhone 15 Pro",
            "iPhone 14",
            "iPhone 13",
            "Galaxy S24",
            "Galaxy S23",
            "Galaxy A54",
            "Pixel 8 Pro",
            "Pixel 7a",
            "Surface Pro 10",
            "ThinkPad X1 Carbon Gen 11",
        ]

        for i in range(34):
            cycle_count = np.random.randint(50, 400)
            nominal_cap = 2.0
            capacity_fade_pct = np.random.uniform(5, 45)
            current_cap = nominal_cap * (1 - capacity_fade_pct / 100)

            device = {
                "device_id": f"DEV-{i:04X}{np.random.randint(0, 255):02X}{np.random.randint(0, 255):02X}{np.random.randint(0, 255):02X}",
                "device_model": device_models[i % len(device_models)],
                "fleet_name": fleet_names[i % len(fleet_names)],
                "cycle_count": cycle_count,
                "current_capacity_ah": round(current_cap, 3),
                "nominal_capacity_ah": nominal_cap,
                "capacity_fade_pct": round(capacity_fade_pct, 1),
                "capacity_fade_rate": round(np.random.uniform(-0.008, -0.001), 4),
                "avg_temperature_exposure_c": round(np.random.uniform(24, 42), 1),
                "max_temperature_c": round(np.random.uniform(30, 55), 1),
                "voltage_drop_rate": round(np.random.uniform(-0.005, -0.0005), 4),
                "internal_resistance_trend": round(np.random.uniform(0.00005, 0.0003), 5),
                "days_since_last_patch": np.random.randint(5, 120),
                "os_version_lag": np.random.randint(0, 4),
                "unpatched_critical_cves": np.random.randint(0, 8),
                "compliance_score": round(np.random.uniform(30, 100), 1),
                "battery_health_score": round(100 - capacity_fade_pct + np.random.normal(0, 5), 1),
                "overall_risk_score": round(np.random.uniform(10, 90), 1),
                "risk_tier": "healthy",
                "remaining_useful_life_days": round(max(5, np.random.exponential(100)), 1),
                "days_to_non_compliance": round(max(0, np.random.exponential(60)), 1),
            }
            # Set risk tier based on score
            rs = device["overall_risk_score"]
            device["risk_tier"] = (
                "healthy" if rs <= 25 else "watch" if rs <= 50 else "warning" if rs <= 75 else "critical"
            )

            devices.append(device)

        return pd.DataFrame(devices)

    def execute(self, arguments: dict) -> dict:
        """
        Execute prediction tool.

        Args:
            arguments: Tool call arguments with optional keys:
                - device_id: specific device to query
                - fleet_name: fleet to query
                - time_horizon_days: risk assessment window (default 30)
                - risk_tier_filter: filter by risk tier

        Returns:
            Dict with prediction results
        """
        device_id = arguments.get("device_id")
        fleet_name = arguments.get("fleet_name")
        time_horizon_days = arguments.get("time_horizon_days", 30)
        risk_tier_filter = arguments.get("risk_tier_filter")

        if self.serving_endpoint and self.databricks_host:
            return self._query_serving_endpoint(device_id, fleet_name, time_horizon_days, risk_tier_filter)
        else:
            return self._query_local(device_id, fleet_name, time_horizon_days, risk_tier_filter)

    def _query_serving_endpoint(self, device_id, fleet_name, time_horizon_days, risk_tier_filter) -> dict:
        """Query Databricks Model Serving endpoint."""
        features_df = self._load_feature_data()

        # Filter data
        if device_id:
            features_df = features_df[features_df["device_id"] == device_id]
        elif fleet_name:
            features_df = features_df[features_df["fleet_name"].str.lower() == fleet_name.lower()]

        if features_df.empty:
            return {"devices": [], "summary": "No devices found matching the query."}

        # Call serving endpoint
        url = f"{self.databricks_host.rstrip('/')}/serving-endpoints/{self.serving_endpoint}/invocations"
        headers = {
            "Authorization": f"Bearer {self.databricks_token}",
            "Content-Type": "application/json",
        }

        try:
            payload = {"dataframe_records": features_df.to_dict(orient="records")}
            response = httpx.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            predictions = response.json().get("predictions", [])
        except Exception as e:
            print(f"Serving endpoint error: {e}. Falling back to local.")
            return self._query_local(device_id, fleet_name, time_horizon_days, risk_tier_filter)

        return self._format_results(predictions, time_horizon_days, risk_tier_filter)

    def _query_local(self, device_id, fleet_name, time_horizon_days, risk_tier_filter) -> dict:
        """Query using local feature data (development mode)."""
        features_df = self._load_feature_data()

        # Filter
        if device_id:
            features_df = features_df[features_df["device_id"] == device_id]
        elif fleet_name:
            features_df = features_df[features_df["fleet_name"].str.lower() == fleet_name.lower()]

        if features_df.empty:
            return {"devices": [], "summary": "No devices found matching the query."}

        # Use feature data as-is for predictions (already has RUL and scores)
        devices = features_df.to_dict(orient="records")
        return self._format_results(devices, time_horizon_days, risk_tier_filter)

    def _format_results(self, devices: list[dict], time_horizon_days: int, risk_tier_filter: str | None) -> dict:
        """Format prediction results for the agent."""
        # Filter by time horizon
        at_risk = [
            d
            for d in devices
            if d.get("remaining_useful_life_days", 9999) <= time_horizon_days
            or d.get("days_to_non_compliance", 9999) <= time_horizon_days
        ]

        # Filter by risk tier
        if risk_tier_filter:
            devices = [d for d in devices if d.get("risk_tier", "").lower() == risk_tier_filter.lower()]

        # Sort by risk (highest first)
        devices.sort(key=lambda d: d.get("overall_risk_score", 0), reverse=True)

        # Build summary
        risk_counts = {"critical": 0, "warning": 0, "watch": 0, "healthy": 0}
        for d in devices:
            tier = d.get("risk_tier", "healthy")
            risk_counts[tier] = risk_counts.get(tier, 0) + 1

        # Determine primary driving factor for each device
        for d in devices:
            factors = []
            if d.get("capacity_fade_pct", 0) > 20:
                factors.append("battery degradation")
            if d.get("days_since_last_patch", 0) > 60:
                factors.append("patch lag")
            if d.get("compliance_score", 100) < 60:
                factors.append("compliance drift")
            if d.get("unpatched_critical_cves", 0) > 3:
                factors.append("unpatched vulnerabilities")
            d["driving_factors"] = factors or ["nominal"]

        summary = (
            f"Fleet assessment ({len(devices)} devices): "
            f"🔴 {risk_counts['critical']} critical, "
            f"🟠 {risk_counts['warning']} warning, "
            f"🟡 {risk_counts['watch']} watch, "
            f"🟢 {risk_counts['healthy']} healthy. "
            f"{len(at_risk)} device(s) predicted to need attention within {time_horizon_days} days."
        )

        return {
            "devices": devices[:20],  # Cap at 20 for response size
            "at_risk_count": len(at_risk),
            "total_count": len(devices),
            "risk_distribution": risk_counts,
            "summary": summary,
        }
