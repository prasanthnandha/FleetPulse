"""
Integration tests for FastAPI endpoints: health, fleet data, and chat.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestAPIEndpoints:
    def test_root_endpoint(self):
        """Verify root endpoint metadata."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "FleetPulse API"
        assert "docs" in data

    def test_health_check(self):
        """Verify /api/health returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "fleetpulse-api"

    def test_fleet_overview(self):
        """Verify /api/fleet/overview returns risk distribution."""
        response = client.get("/api/fleet/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_devices" in data
        assert "risk_distribution" in data
        assert "healthy" in data["risk_distribution"]
        assert "critical" in data["risk_distribution"]
        assert "avg_risk_score" in data

    def test_fleet_devices_list(self):
        """Verify /api/fleet/devices returns device list with filtering."""
        response = client.get("/api/fleet/devices?limit=10")
        assert response.status_code == 200
        devices = response.json()
        assert isinstance(devices, list)
        assert len(devices) <= 10
        if len(devices) > 0:
            first = devices[0]
            assert "device_id" in first
            assert "risk_tier" in first
            assert "overall_risk_score" in first

    def test_fleet_trends(self):
        """Verify /api/fleet/trends returns time series data."""
        response = client.get("/api/fleet/trends?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "trend_data" in data
        assert len(data["trend_data"]) > 0
        point = data["trend_data"][0]
        assert "date" in point
        assert "avg_risk_score" in point
