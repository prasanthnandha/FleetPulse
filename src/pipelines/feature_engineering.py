"""
FleetPulse — Feature Engineering Pipeline
==========================================
PySpark job that reads raw battery cycle data + CVE/patch data + device inventory,
computes rolling degradation features per device, and writes to the feature table.

Usage (Databricks):
    dbutils.widgets.text("battery_table", "fleetpulse.raw.battery_cycles")
    dbutils.widgets.text("cve_table", "fleetpulse.raw.cve_patches")
    dbutils.widgets.text("inventory_table", "fleetpulse.raw.device_inventory")
    dbutils.widgets.text("output_table", "fleetpulse.features.device_health")

Usage (local):
    python -m src.pipelines.feature_engineering --synthetic
"""

import argparse
from datetime import datetime

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, IntegerType

from src.pipelines.utils.transforms import (
    assign_risk_tier,
    compute_battery_health_score,
    compute_compliance_score,
    estimate_rul_label,
    rolling_slope_udf,
)


def build_battery_features(spark: SparkSession, battery_table: str) -> DataFrame:
    """
    Compute battery health features from raw cycle data.

    Features:
        - cycle_count: total discharge cycles per device
        - current_capacity_ah: most recent measured capacity
        - nominal_capacity_ah: original rated capacity
        - capacity_fade_pct: percent capacity lost
        - capacity_fade_rate: linear slope of capacity over last 50 cycles
        - avg_temperature_exposure_c: mean discharge temperature (last 50 cycles)
        - max_temperature_c: peak temperature observed
        - voltage_drop_rate: rate of end-of-discharge voltage decline
        - internal_resistance_trend: slope of resistance growth
    """
    df = spark.table(battery_table) if "." in battery_table else spark.read.format("delta").load(battery_table)

    # Filter to discharge cycles only (capacity measurements)
    discharge = df.filter(F.col("cycle_type") == "discharge")

    # ── Per-device aggregations ──────────────────────────────────────────
    w_all = Window.partitionBy("device_id").orderBy("cycle_number")
    w_recent = Window.partitionBy("device_id").orderBy("cycle_number").rowsBetween(-50, 0)

    # Get per-cycle scalar temperature (mean of the temperature array)
    discharge = discharge.withColumn(
        "cycle_avg_temp",
        F.when(
            F.col("temperature_measured_c").isNotNull(),
            F.aggregate(
                F.col("temperature_measured_c"),
                F.lit(0.0).cast(FloatType()),
                lambda acc, x: acc + x,
            )
            / F.size(F.col("temperature_measured_c")),
        ).otherwise(F.col("ambient_temperature_c")),
    )

    # End-of-discharge voltage (last element of voltage array)
    discharge = discharge.withColumn(
        "eod_voltage",
        F.when(
            F.col("voltage_measured_v").isNotNull(),
            F.element_at(F.col("voltage_measured_v"), -1),
        ),
    )

    # ── Rolling window features ──────────────────────────────────────────
    discharge = (
        discharge.withColumn("capacity_rolling_mean", F.avg("capacity_ah").over(w_recent))
        .withColumn("temp_rolling_mean", F.avg("cycle_avg_temp").over(w_recent))
        .withColumn("temp_max", F.max("cycle_avg_temp").over(w_all))
        .withColumn("eod_voltage_rolling_mean", F.avg("eod_voltage").over(w_recent))
        .withColumn("resistance_rolling_mean", F.avg("internal_resistance_ohm").over(w_recent))
    )

    # ── Take the latest snapshot per device ──────────────────────────────
    w_rank = Window.partitionBy("device_id").orderBy(F.col("cycle_number").desc())
    latest = discharge.withColumn("_rank", F.row_number().over(w_rank)).filter(F.col("_rank") == 1).drop("_rank")

    # ── Compute capacity fade rate via collect_list + UDF ────────────────
    # Collect last 50 capacity values per device, compute slope
    slope_fn = rolling_slope_udf()

    capacity_series = (
        discharge.filter(F.col("capacity_ah").isNotNull())
        .groupBy("device_id")
        .agg(
            F.sort_array(F.collect_list(F.struct(F.col("cycle_number"), F.col("capacity_ah")))).alias(
                "capacity_series"
            ),
            F.count("*").alias("cycle_count"),
        )
    )

    # Extract sorted capacity values
    capacity_series = capacity_series.withColumn(
        "capacity_values",
        F.transform(F.col("capacity_series"), lambda x: x["capacity_ah"]),
    )
    capacity_series = capacity_series.withColumn(
        "capacity_fade_rate",
        slope_fn(F.col("capacity_values")),
    )

    # Similarly for voltage and resistance trends
    voltage_series = (
        discharge.filter(F.col("eod_voltage").isNotNull())
        .groupBy("device_id")
        .agg(
            F.sort_array(F.collect_list(F.struct(F.col("cycle_number"), F.col("eod_voltage")))).alias("voltage_series"),
        )
    )
    voltage_series = voltage_series.withColumn(
        "voltage_values",
        F.transform(F.col("voltage_series"), lambda x: x["eod_voltage"]),
    )
    voltage_series = voltage_series.withColumn(
        "voltage_drop_rate",
        slope_fn(F.col("voltage_values")),
    )

    resistance_series = (
        discharge.filter(F.col("internal_resistance_ohm").isNotNull())
        .groupBy("device_id")
        .agg(
            F.sort_array(F.collect_list(F.struct(F.col("cycle_number"), F.col("internal_resistance_ohm")))).alias(
                "resistance_series"
            ),
        )
    )
    resistance_series = resistance_series.withColumn(
        "resistance_values",
        F.transform(F.col("resistance_series"), lambda x: x["internal_resistance_ohm"]),
    )
    resistance_series = resistance_series.withColumn(
        "internal_resistance_trend",
        slope_fn(F.col("resistance_values")),
    )

    # ── Join everything ──────────────────────────────────────────────────
    battery_features = (
        latest.select(
            "device_id",
            "device_model",
            F.col("capacity_ah").alias("current_capacity_ah"),
            "nominal_capacity_ah",
            F.col("temp_rolling_mean").alias("avg_temperature_exposure_c"),
            F.col("temp_max").alias("max_temperature_c"),
        )
        .join(
            capacity_series.select("device_id", "cycle_count", "capacity_fade_rate"),
            on="device_id",
            how="left",
        )
        .join(
            voltage_series.select("device_id", "voltage_drop_rate"),
            on="device_id",
            how="left",
        )
        .join(
            resistance_series.select("device_id", "internal_resistance_trend"),
            on="device_id",
            how="left",
        )
    )

    # Capacity fade percentage
    battery_features = battery_features.withColumn(
        "capacity_fade_pct",
        ((F.col("nominal_capacity_ah") - F.col("current_capacity_ah")) / F.col("nominal_capacity_ah") * 100.0).cast(
            FloatType()
        ),
    )

    return battery_features


def build_compliance_features(spark: SparkSession, cve_table: str, inventory_table: str) -> DataFrame:
    """
    Compute compliance/patch-lag features from CVE data and device inventory.

    Features:
        - days_since_last_patch: days since the device's OS was last patched
        - os_version_lag: number of OS versions behind the latest
        - unpatched_critical_cves: count of unpatched HIGH/CRITICAL CVEs for device's OS
    """
    cve_df = spark.table(cve_table) if "." in cve_table else spark.read.format("delta").load(cve_table)
    inv_df = (
        spark.table(inventory_table) if "." in inventory_table else spark.read.format("delta").load(inventory_table)
    )

    now = F.current_timestamp()

    # ── Count unpatched critical CVEs per OS ──────────────────────────────
    unpatched_cves = (
        cve_df.filter((F.col("severity").isin("HIGH", "CRITICAL")) & (F.col("patch_available") == "false"))
        .groupBy("affected_os")
        .agg(F.count("*").alias("unpatched_critical_cves"))
    )

    # ── Compute patch freshness per OS ───────────────────────────────────
    latest_patch = (
        cve_df.filter(F.col("patch_date").isNotNull())
        .groupBy("affected_os")
        .agg(F.max("patch_date").alias("latest_patch_date"))
    )

    # ── OS version lag ───────────────────────────────────────────────────
    # Simple heuristic: compare os_version to latest_os_version
    # Convert version strings to comparable numbers
    inv_enriched = (
        inv_df.join(unpatched_cves, inv_df["os_type"] == unpatched_cves["affected_os"], "left")
        .join(latest_patch, inv_df["os_type"] == latest_patch["affected_os"], "left")
        .withColumn(
            "days_since_last_patch",
            F.when(
                F.col("latest_patch_date").isNotNull(),
                F.datediff(now, F.col("latest_patch_date")),
            ).otherwise(F.lit(90)),  # Default: assume 90 days if unknown
        )
        .withColumn(
            "os_version_lag",
            F.when(F.col("os_version") == F.col("latest_os_version"), F.lit(0)).otherwise(
                # Simple heuristic: extract major version numbers
                F.abs(
                    F.regexp_extract(F.col("latest_os_version"), r"(\d+)", 1).cast(IntegerType())
                    - F.regexp_extract(F.col("os_version"), r"(\d+)", 1).cast(IntegerType())
                )
            ),
        )
        .fillna({"unpatched_critical_cves": 0, "os_version_lag": 0, "days_since_last_patch": 90})
    )

    compliance_features = inv_enriched.select(
        "device_id",
        "fleet_name",
        "days_since_last_patch",
        "os_version_lag",
        "unpatched_critical_cves",
        "encryption_enabled",
        "passcode_set",
    )

    return compliance_features


def run_feature_engineering(
    spark: SparkSession,
    battery_table: str,
    cve_table: str,
    inventory_table: str,
    output_table: str,
):
    """
    Main feature engineering pipeline.
    Joins battery features + compliance features, computes derived scores,
    and writes the final device_health feature table.
    """
    now = datetime.utcnow()

    # ── Build feature sets ───────────────────────────────────────────────
    print("Building battery features...")
    battery_feats = build_battery_features(spark, battery_table)

    print("Building compliance features...")
    compliance_feats = build_compliance_features(spark, cve_table, inventory_table)

    # ── Join battery + compliance ────────────────────────────────────────
    print("Joining feature sets...")
    features = battery_feats.join(compliance_feats, on="device_id", how="inner")

    # ── Compute composite scores ─────────────────────────────────────────
    print("Computing composite scores...")

    # Compliance score
    features = features.withColumn(
        "compliance_score",
        compute_compliance_score(
            "days_since_last_patch",
            "os_version_lag",
            "unpatched_critical_cves",
            "encryption_enabled",
            "passcode_set",
        ),
    )

    # Battery health score
    features = features.withColumn(
        "battery_health_score",
        compute_battery_health_score(
            "capacity_fade_pct",
            "cycle_count",
            "avg_temperature_exposure_c",
        ),
    )

    # Overall risk score (inverse of health — higher = riskier)
    features = features.withColumn(
        "overall_risk_score",
        (F.lit(100.0) - (F.col("battery_health_score") * 0.5 + F.col("compliance_score") * 0.5)).cast(FloatType()),
    )

    # Risk tier
    features = features.withColumn(
        "risk_tier",
        assign_risk_tier("overall_risk_score"),
    )

    # ── Estimate target labels (for model training) ──────────────────────
    features = features.withColumn(
        "remaining_useful_life_days",
        estimate_rul_label(
            "capacity_fade_rate",
            "current_capacity_ah",
            failure_threshold_pct=30.0,
            nominal_capacity_col="nominal_capacity_ah",
        ),
    )

    # Days to non-compliance (heuristic: based on patch lag trend)
    features = features.withColumn(
        "days_to_non_compliance",
        F.when(F.col("compliance_score") < 50, F.lit(0.0))
        .when(
            F.col("compliance_score") < 70,
            (F.col("compliance_score") - 50.0) * 1.5,
        )
        .otherwise(
            (F.col("compliance_score") - 50.0) * 3.0,
        )
        .cast(FloatType()),
    )

    # ── Add metadata columns ─────────────────────────────────────────────
    features = features.withColumn("snapshot_date", F.lit(now)).withColumn("updated_at", F.lit(now))

    # ── Select final columns ─────────────────────────────────────────────
    final_columns = [
        "device_id",
        "device_model",
        "fleet_name",
        "snapshot_date",
        # Battery features
        "cycle_count",
        "current_capacity_ah",
        "nominal_capacity_ah",
        "capacity_fade_pct",
        "capacity_fade_rate",
        "avg_temperature_exposure_c",
        "max_temperature_c",
        "voltage_drop_rate",
        "internal_resistance_trend",
        # Compliance features
        "days_since_last_patch",
        "os_version_lag",
        "unpatched_critical_cves",
        "compliance_score",
        # Derived scores
        "battery_health_score",
        "overall_risk_score",
        "risk_tier",
        # Labels
        "remaining_useful_life_days",
        "days_to_non_compliance",
        "updated_at",
    ]
    output_df = features.select([c for c in final_columns if c in features.columns])

    # ── Write to Delta ───────────────────────────────────────────────────
    row_count = output_df.count()
    print(f"Writing {row_count} device health records to {output_table}...")
    output_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(output_table)
    print("Feature engineering complete.")

    # Print summary stats
    print("\n── Feature Summary ──")
    output_df.select(
        F.count("*").alias("total_devices"),
        F.avg("overall_risk_score").alias("avg_risk_score"),
        F.avg("battery_health_score").alias("avg_battery_health"),
        F.avg("compliance_score").alias("avg_compliance_score"),
        F.avg("remaining_useful_life_days").alias("avg_rul_days"),
    ).show(truncate=False)

    output_df.groupBy("risk_tier").count().orderBy("risk_tier").show()

    return output_df


# ==============================================================================
# CLI entrypoint
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse Feature Engineering")
    parser.add_argument("--battery-table", default="fleetpulse.raw.battery_cycles")
    parser.add_argument("--cve-table", default="fleetpulse.raw.cve_patches")
    parser.add_argument("--inventory-table", default="fleetpulse.raw.device_inventory")
    parser.add_argument("--output-table", default="fleetpulse.features.device_health")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("FleetPulse-FeatureEngineering")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )

    run_feature_engineering(
        spark,
        battery_table=args.battery_table,
        cve_table=args.cve_table,
        inventory_table=args.inventory_table,
        output_table=args.output_table,
    )
