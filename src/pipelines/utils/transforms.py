"""
FleetPulse — Reusable PySpark Transforms & UDFs
================================================
Stateless transform functions for feature engineering.
All functions operate on PySpark DataFrames or columns.
"""


import numpy as np
from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType

# ==============================================================================
# Rolling Slope (Linear Regression over a window)
# ==============================================================================

def rolling_slope_udf():
    """
    Returns a PySpark UDF that computes the slope of a simple linear regression
    over an array of float values.

    Usage:
        slope_fn = rolling_slope_udf()
        df.withColumn("fade_rate", slope_fn(F.collect_list("capacity_ah")))
    """

    def _compute_slope(values: list[float]) -> float | None:
        if not values or len(values) < 2:
            return None
        arr = np.array(values, dtype=np.float64)
        # Remove NaNs
        mask = ~np.isnan(arr)
        arr = arr[mask]
        if len(arr) < 2:
            return None
        x = np.arange(len(arr), dtype=np.float64)
        # Simple least-squares slope: β = Σ((x-x̄)(y-ȳ)) / Σ((x-x̄)²)
        x_mean = x.mean()
        y_mean = arr.mean()
        numerator = ((x - x_mean) * (arr - y_mean)).sum()
        denominator = ((x - x_mean) ** 2).sum()
        if denominator == 0:
            return 0.0
        return float(numerator / denominator)

    return F.udf(_compute_slope, FloatType())


# ==============================================================================
# Exponential Weighted Moving Average
# ==============================================================================

def ewma_udf(alpha: float = 0.3):
    """
    Returns a PySpark UDF that computes the exponential weighted moving average
    of an array of float values.

    Args:
        alpha: Smoothing factor (0 < alpha <= 1). Higher = more weight on recent values.
    """

    def _compute_ewma(values: list[float]) -> float | None:
        if not values:
            return None
        arr = np.array(values, dtype=np.float64)
        mask = ~np.isnan(arr)
        arr = arr[mask]
        if len(arr) == 0:
            return None
        ewma_val = arr[0]
        for v in arr[1:]:
            ewma_val = alpha * v + (1 - alpha) * ewma_val
        return float(ewma_val)

    return F.udf(_compute_ewma, FloatType())


# ==============================================================================
# Compliance Score
# ==============================================================================

def compute_compliance_score(
    days_since_patch_col: str | Column,
    os_version_lag_col: str | Column,
    unpatched_cves_col: str | Column,
    encryption_col: str | Column,
    passcode_col: str | Column,
) -> Column:
    """
    Compute a composite compliance score (0–100, 100 = fully compliant).

    Formula:
        - Patch freshness:   max(0, 100 - days_since_patch * 1.5)   → weight 25%
        - OS currency:       max(0, 100 - os_version_lag * 20)      → weight 25%
        - Vulnerability:     max(0, 100 - unpatched_cves * 15)      → weight 30%
        - Security config:   50*encryption + 50*passcode             → weight 20%
    """
    patch_score = F.greatest(F.lit(0.0), F.lit(100.0) - F.col(days_since_patch_col) * 1.5)
    os_score = F.greatest(F.lit(0.0), F.lit(100.0) - F.col(os_version_lag_col) * 20.0)
    vuln_score = F.greatest(F.lit(0.0), F.lit(100.0) - F.col(unpatched_cves_col) * 15.0)

    sec_score = (
        F.when(F.col(encryption_col) == "true", F.lit(50.0)).otherwise(F.lit(0.0))
        + F.when(F.col(passcode_col) == "true", F.lit(50.0)).otherwise(F.lit(0.0))
    )

    return (
        patch_score * 0.25
        + os_score * 0.25
        + vuln_score * 0.30
        + sec_score * 0.20
    ).cast(FloatType())


# ==============================================================================
# Battery Health Score
# ==============================================================================

def compute_battery_health_score(
    capacity_fade_pct_col: str | Column,
    cycle_count_col: str | Column,
    avg_temp_col: str | Column,
    max_expected_cycles: int = 500,
) -> Column:
    """
    Compute a battery health score (0–100, 100 = perfect health).

    Components:
        - Capacity retention: (100 - capacity_fade_pct)              → weight 50%
        - Cycle life remaining: (1 - cycle_count/max_cycles) * 100   → weight 30%
        - Thermal stress:      max(0, 100 - max(0, avg_temp-30)*5)   → weight 20%
    """
    capacity_score = F.lit(100.0) - F.col(capacity_fade_pct_col)
    cycle_score = (F.lit(1.0) - F.col(cycle_count_col) / F.lit(float(max_expected_cycles))) * 100.0
    cycle_score = F.greatest(F.lit(0.0), cycle_score)
    thermal_score = F.greatest(
        F.lit(0.0),
        F.lit(100.0) - F.greatest(F.lit(0.0), F.col(avg_temp_col) - F.lit(30.0)) * 5.0,
    )

    return F.greatest(
        F.lit(0.0),
        F.least(
            F.lit(100.0),
            capacity_score * 0.50 + cycle_score * 0.30 + thermal_score * 0.20,
        ),
    ).cast(FloatType())


# ==============================================================================
# Risk Tier Classification
# ==============================================================================

def assign_risk_tier(risk_score_col: str | Column) -> Column:
    """
    Classify overall risk score into tiers.

    - 0-25:  "healthy"
    - 26-50: "watch"
    - 51-75: "warning"
    - 76-100: "critical"
    """
    return (
        F.when(F.col(risk_score_col) <= 25, F.lit("healthy"))
        .when(F.col(risk_score_col) <= 50, F.lit("watch"))
        .when(F.col(risk_score_col) <= 75, F.lit("warning"))
        .otherwise(F.lit("critical"))
    )


# ==============================================================================
# Windowed Aggregations
# ==============================================================================

def add_rolling_features(
    df: DataFrame,
    partition_col: str,
    order_col: str,
    value_col: str,
    window_size: int = 20,
    prefix: str = "",
) -> DataFrame:
    """
    Add rolling window features (mean, std, min, max) for a given value column.

    Args:
        df: Input DataFrame
        partition_col: Column to partition by (e.g., "device_id")
        order_col: Column to order by (e.g., "cycle_number")
        value_col: Column to compute rolling stats over
        window_size: Number of preceding rows in the window
        prefix: Column name prefix for output columns
    """
    w = Window.partitionBy(partition_col).orderBy(order_col).rowsBetween(-window_size, 0)
    p = prefix or value_col

    return (
        df
        .withColumn(f"{p}_rolling_mean", F.avg(F.col(value_col)).over(w))
        .withColumn(f"{p}_rolling_std", F.stddev(F.col(value_col)).over(w))
        .withColumn(f"{p}_rolling_min", F.min(F.col(value_col)).over(w))
        .withColumn(f"{p}_rolling_max", F.max(F.col(value_col)).over(w))
    )


# ==============================================================================
# Remaining Useful Life Estimation (heuristic label)
# ==============================================================================

def estimate_rul_label(
    capacity_fade_rate_col: str | Column,
    current_capacity_col: str | Column,
    failure_threshold_pct: float = 30.0,
    nominal_capacity_col: str | Column = "nominal_capacity_ah",
) -> Column:
    """
    Heuristic label for remaining useful life (days) based on linear extrapolation
    of capacity fade rate.

    RUL = (current_capacity - failure_capacity) / |fade_rate_per_day|

    Assumes fade_rate is in Ah/cycle and ~1 cycle/day for enterprise devices.
    A device is "failed" when capacity drops below (100 - failure_threshold_pct)% of nominal.
    """
    failure_capacity = F.col(nominal_capacity_col) * (1.0 - failure_threshold_pct / 100.0)
    remaining_capacity = F.col(current_capacity_col) - failure_capacity

    # fade_rate is negative (capacity decreasing), so we negate
    daily_fade = F.abs(F.col(capacity_fade_rate_col))

    rul = F.when(
        daily_fade > 0.0001,  # Avoid division by near-zero
        remaining_capacity / daily_fade,
    ).otherwise(F.lit(9999.0))  # Essentially no degradation detected

    return F.greatest(F.lit(0.0), rul).cast(FloatType())
