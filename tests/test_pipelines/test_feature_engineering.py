import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark required for pipeline schema definitions")

from src.pipelines.utils.schema import (  # noqa: E402
    BATTERY_CYCLES_SCHEMA,
    CVE_PATCHES_SCHEMA,
    DEVICE_HEALTH_FEATURES_SCHEMA,
    DOCUMENT_CHUNKS_SCHEMA,
)


class TestPipelineSchemas:
    def test_battery_cycles_schema_fields(self):
        """Verify battery cycle schema includes required predictive columns."""
        field_names = [f.name for f in BATTERY_CYCLES_SCHEMA.fields]
        assert "device_id" in field_names
        assert "capacity_ah" in field_names
        assert "voltage_measured_v" in field_names
        assert "cycle_number" in field_names

    def test_cve_patches_schema_fields(self):
        """Verify CVE patch schema fields."""
        field_names = [f.name for f in CVE_PATCHES_SCHEMA.fields]
        assert "cve_id" in field_names
        assert "cvss_score" in field_names
        assert "affected_os" in field_names

    def test_device_health_features_schema_fields(self):
        """Verify final engineered features table schema."""
        field_names = [f.name for f in DEVICE_HEALTH_FEATURES_SCHEMA.fields]
        assert "device_id" in field_names
        assert "capacity_fade_rate" in field_names
        assert "battery_health_score" in field_names
        assert "compliance_score" in field_names
        assert "overall_risk_score" in field_names
        assert "risk_tier" in field_names
        assert "remaining_useful_life_days" in field_names

    def test_document_chunks_schema_fields(self):
        """Verify RAG document chunk schema."""
        field_names = [f.name for f in DOCUMENT_CHUNKS_SCHEMA.fields]
        assert "chunk_id" in field_names
        assert "chunk_text" in field_names
        assert "embedding" in field_names
        assert "device_model" in field_names
        assert "component_type" in field_names
