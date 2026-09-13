"""
FleetPulse — Delta Table Schemas
=================================
PySpark StructType definitions for all Delta tables used in the pipeline.
"""

from pyspark.sql.types import (
    ArrayType,
    FloatType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# ==============================================================================
# Raw Layer — fleetpulse.raw.*
# ==============================================================================

BATTERY_CYCLES_SCHEMA = StructType(
    [
        StructField("device_id", StringType(), nullable=False),
        StructField("device_model", StringType(), nullable=False),
        StructField("battery_id", StringType(), nullable=False),
        StructField("cycle_number", IntegerType(), nullable=False),
        StructField("cycle_type", StringType(), nullable=False),  # "charge" | "discharge"
        StructField("ambient_temperature_c", FloatType(), nullable=True),
        StructField("voltage_measured_v", ArrayType(FloatType()), nullable=True),
        StructField("current_measured_a", ArrayType(FloatType()), nullable=True),
        StructField("temperature_measured_c", ArrayType(FloatType()), nullable=True),
        StructField("time_s", ArrayType(FloatType()), nullable=True),
        StructField("capacity_ah", FloatType(), nullable=True),  # Measured capacity this cycle
        StructField("nominal_capacity_ah", FloatType(), nullable=True),  # Original rated capacity
        StructField("internal_resistance_ohm", FloatType(), nullable=True),
        StructField("cycle_duration_s", FloatType(), nullable=True),
        StructField("timestamp", TimestampType(), nullable=False),
        StructField("ingestion_timestamp", TimestampType(), nullable=False),
    ]
)
"""
Raw battery cycle data from NASA PCoE dataset, mapped to synthetic device IDs.
Each row = one charge/discharge cycle for a battery/device.
"""

CVE_PATCHES_SCHEMA = StructType(
    [
        StructField("cve_id", StringType(), nullable=False),
        StructField("published_date", TimestampType(), nullable=False),
        StructField("last_modified_date", TimestampType(), nullable=True),
        StructField("description", StringType(), nullable=True),
        StructField("severity", StringType(), nullable=True),  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
        StructField("cvss_score", FloatType(), nullable=True),
        StructField("affected_os", StringType(), nullable=True),  # "iOS" | "Android" | "Windows"
        StructField("affected_versions", ArrayType(StringType()), nullable=True),
        StructField("patch_available", StringType(), nullable=True),  # "true" | "false"
        StructField("patch_date", TimestampType(), nullable=True),
        StructField("ingestion_timestamp", TimestampType(), nullable=False),
    ]
)
"""
CVE/patch data from NVD feed, filtered for mobile OS vulnerabilities.
"""

DEVICE_INVENTORY_SCHEMA = StructType(
    [
        StructField("device_id", StringType(), nullable=False),
        StructField("device_model", StringType(), nullable=False),
        StructField("manufacturer", StringType(), nullable=False),
        StructField("os_type", StringType(), nullable=False),  # "iOS" | "Android" | "Windows"
        StructField("os_version", StringType(), nullable=False),
        StructField("latest_os_version", StringType(), nullable=True),
        StructField("fleet_name", StringType(), nullable=False),  # "Sales" | "Engineering" | "Executive" | etc.
        StructField("assigned_user", StringType(), nullable=True),
        StructField("enrollment_date", TimestampType(), nullable=False),
        StructField("last_checkin", TimestampType(), nullable=True),
        StructField("mdm_compliant", StringType(), nullable=True),  # "true" | "false"
        StructField("encryption_enabled", StringType(), nullable=True),
        StructField("passcode_set", StringType(), nullable=True),
    ]
)
"""
Synthetic device inventory — maps device IDs to fleet membership and MDM attributes.
"""

# ==============================================================================
# Feature Layer — fleetpulse.features.*
# ==============================================================================

DEVICE_HEALTH_SCHEMA = StructType(
    [
        StructField("device_id", StringType(), nullable=False),
        StructField("device_model", StringType(), nullable=False),
        StructField("fleet_name", StringType(), nullable=False),
        StructField("snapshot_date", TimestampType(), nullable=False),
        # Battery health features
        StructField("cycle_count", IntegerType(), nullable=True),
        StructField("current_capacity_ah", FloatType(), nullable=True),
        StructField("nominal_capacity_ah", FloatType(), nullable=True),
        StructField("capacity_fade_pct", FloatType(), nullable=True),  # (nominal - current) / nominal * 100
        StructField("capacity_fade_rate", FloatType(), nullable=True),  # Linear slope over last N cycles
        StructField("avg_temperature_exposure_c", FloatType(), nullable=True),  # Rolling mean temp
        StructField("max_temperature_c", FloatType(), nullable=True),
        StructField("voltage_drop_rate", FloatType(), nullable=True),  # Rate of EOD voltage decline
        StructField("internal_resistance_trend", FloatType(), nullable=True),  # Slope of resistance growth
        # Compliance / patch features
        StructField("days_since_last_patch", IntegerType(), nullable=True),
        StructField("os_version_lag", IntegerType(), nullable=True),  # Versions behind latest
        StructField("unpatched_critical_cves", IntegerType(), nullable=True),
        StructField("compliance_score", FloatType(), nullable=True),  # 0-100 composite
        # Derived risk features
        StructField("battery_health_score", FloatType(), nullable=True),  # 0-100
        StructField("overall_risk_score", FloatType(), nullable=True),  # 0-100 (higher = riskier)
        StructField("risk_tier", StringType(), nullable=True),  # "healthy" | "watch" | "warning" | "critical"
        # Target variables (for model training)
        StructField("remaining_useful_life_days", FloatType(), nullable=True),
        StructField("days_to_non_compliance", FloatType(), nullable=True),
        StructField("updated_at", TimestampType(), nullable=False),
    ]
)
"""
Feature table for ML model training and serving.
One row per device per snapshot date — computed by the feature engineering pipeline.
"""

# ==============================================================================
# RAG Layer — fleetpulse.rag.*
# ==============================================================================

DOCUMENT_CHUNKS_SCHEMA = StructType(
    [
        StructField("chunk_id", StringType(), nullable=False),
        StructField("document_id", StringType(), nullable=False),
        StructField("document_type", StringType(), nullable=False),  # "parts_catalog" | "service_manual"
        StructField("device_model", StringType(), nullable=True),
        StructField("component_type", StringType(), nullable=True),  # "battery" | "screen" | "logic_board" | etc.
        StructField("chunk_text", StringType(), nullable=False),
        StructField("chunk_index", IntegerType(), nullable=False),
        StructField("embedding", ArrayType(FloatType()), nullable=True),
        StructField("metadata_json", StringType(), nullable=True),  # Additional structured metadata as JSON
        StructField("created_at", TimestampType(), nullable=False),
    ]
)
"""
Chunked and embedded documents for Vector Search.
Contains both parts catalog entries and service manual chunks.
"""

# Alias for backward compatibility and test clarity
DEVICE_HEALTH_FEATURES_SCHEMA = DEVICE_HEALTH_SCHEMA
