# Databricks notebook source
# MAGIC %md
# MAGIC # FleetPulse — 01: Data Ingestion & Feature Exploration
# MAGIC
# MAGIC This notebook explores:
# MAGIC 1. Raw NASA battery cycle degradation data
# MAGIC 2. NVD CVE vulnerability feeds and patch-lag calculation
# MAGIC 3. Feature engineering: rolling capacity fade, thermal exposure, compliance drift

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1. Environment Setup & Configuration

# COMMAND ----------

import os
from pyspark.sql import functions as F
from pyspark.sql import Window

# Widgets for Databricks execution
dbutils.widgets.text("catalog", "fleetpulse", "Unity Catalog Name")
dbutils.widgets.text("schema", "dev", "Database Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

print(f"Target Catalog: {catalog}.{schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2. Inspect Raw Battery Cycles Data

# COMMAND ----------

# Read raw battery cycles Delta table
battery_cycles_df = spark.table(f"{catalog}.{schema}.battery_cycles")
display(battery_cycles_df.limit(10))

# COMMAND ----------

# Aggregate statistics per device model
cycle_stats = (
    battery_cycles_df
    .groupBy("device_model")
    .agg(
        F.countDistinct("device_id").alias("device_count"),
        F.avg("capacity_ah").alias("avg_capacity_ah"),
        F.max("cycle_number").alias("max_cycles"),
        F.avg("ambient_temperature_c").alias("avg_temp_c"),
    )
)
display(cycle_stats)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3. Inspect CVE & Security Patch Lag

# COMMAND ----------

cve_df = spark.table(f"{catalog}.{schema}.cve_patches")
display(cve_df.groupBy("severity", "affected_os").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4. Device Health Feature Table Overview

# COMMAND ----------

features_df = spark.table(f"{catalog}.{schema}.device_health")
display(
    features_df
    .select(
        "device_id", "device_model", "fleet_name",
        "battery_health_score", "compliance_score",
        "overall_risk_score", "risk_tier",
        "remaining_useful_life_days"
    )
    .orderBy(F.col("overall_risk_score").desc())
    .limit(20)
)
