"""
FleetPulse — Model Evaluation & Comparison
============================================
Loads candidate models from MLflow, evaluates on holdout set,
and generates comparison reports.

Usage:
    python -m src.models.evaluate \
        --experiment-name "/FleetPulse/RUL-Predictor" \
        --feature-table ./data/processed/device_health/
"""

import argparse

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)


def load_experiment_runs(experiment_name: str, max_runs: int = 10) -> pd.DataFrame:
    """
    Load recent runs from an MLflow experiment.

    Returns:
        DataFrame with run_id, metrics, and params for each run.
    """
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"Experiment '{experiment_name}' not found")
        return pd.DataFrame()

    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.test_rmse ASC"],
        max_results=max_runs,
    )

    if runs.empty:
        print(f"No runs found in experiment '{experiment_name}'")
        return pd.DataFrame()

    print(f"Found {len(runs)} runs in '{experiment_name}'")
    return runs


def evaluate_model_on_holdout(
    model_uri: str,
    X_holdout: pd.DataFrame,
    y_holdout: pd.Series,
    model_type: str = "regression",
) -> dict:
    """
    Evaluate a logged MLflow model on a holdout set.

    Args:
        model_uri: MLflow model URI (e.g., "runs:/<run_id>/model")
        X_holdout: Feature DataFrame
        y_holdout: True target values
        model_type: "regression" or "anomaly"

    Returns:
        Dict of evaluation metrics
    """
    model = mlflow.pyfunc.load_model(model_uri)
    y_pred = model.predict(X_holdout)

    if model_type == "regression":
        metrics = {
            "holdout_rmse": float(np.sqrt(mean_squared_error(y_holdout, y_pred))),
            "holdout_mae": float(mean_absolute_error(y_holdout, y_pred)),
            "holdout_r2": float(r2_score(y_holdout, y_pred)),
            "holdout_mape": float(mean_absolute_percentage_error(y_holdout, y_pred)),
        }

        # Error distribution analysis
        errors = y_holdout.values - y_pred
        metrics.update({
            "error_mean": float(np.mean(errors)),
            "error_std": float(np.std(errors)),
            "error_p95": float(np.percentile(np.abs(errors), 95)),
            "error_max": float(np.max(np.abs(errors))),
        })

    elif model_type == "anomaly":
        # Isolation Forest: predictions are 1 (normal) or -1 (anomaly)
        n_anomalies = int((y_pred == -1).sum()) if hasattr(y_pred, '__len__') else 0
        metrics = {
            "num_anomalies": n_anomalies,
            "anomaly_rate": float(n_anomalies / len(y_pred)) if len(y_pred) > 0 else 0,
        }

    else:
        metrics = {}

    return metrics


def compare_models(experiment_name: str, feature_table: str, use_spark: bool = True):
    """
    Compare all models in an experiment on the same holdout data.
    Prints a comparison table.
    """
    # Load data
    if use_spark:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName("FleetPulse-Evaluate").getOrCreate()
        if "." in feature_table:
            df = spark.table(feature_table).toPandas()
        else:
            df = spark.read.format("delta").load(feature_table).toPandas()
    else:
        if feature_table.endswith(".csv"):
            df = pd.read_csv(feature_table)
        else:
            df = pd.read_parquet(feature_table)

    # Load experiment runs
    runs_df = load_experiment_runs(experiment_name)
    if runs_df.empty:
        return

    # Prepare holdout data (last 20%)
    from src.models.train_rul_model import prepare_data

    target_col = "remaining_useful_life_days"
    if target_col not in df.columns:
        print(f"Target column '{target_col}' not found")
        return

    _, X_holdout, _, y_holdout, features = prepare_data(df, target_col, test_size=0.2)

    print(f"\n{'='*80}")
    print(f"Model Comparison — {experiment_name}")
    print(f"Holdout size: {len(X_holdout)} samples")
    print(f"{'='*80}")

    comparison = []
    for _, run in runs_df.iterrows():
        run_id = run["run_id"]
        model_uri = f"runs:/{run_id}/model"

        try:
            metrics = evaluate_model_on_holdout(model_uri, X_holdout, y_holdout)
            comparison.append({
                "run_id": run_id[:8],
                "run_name": run.get("tags.mlflow.runName", ""),
                **metrics,
            })
        except Exception as e:
            print(f"  Skipping run {run_id[:8]}: {e}")

    if comparison:
        comp_df = pd.DataFrame(comparison)
        print(comp_df.to_string(index=False, float_format="%.4f"))

        # Highlight best model
        best_idx = comp_df["holdout_rmse"].idxmin()
        best = comp_df.loc[best_idx]
        print(f"\n🏆 Best model: {best['run_id']} (RMSE: {best['holdout_rmse']:.4f}, R²: {best['holdout_r2']:.4f})")

    return comparison


# ==============================================================================
# CLI entrypoint
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse Model Evaluation")
    parser.add_argument("--experiment-name", default="/FleetPulse/RUL-Predictor")
    parser.add_argument("--feature-table", default="fleetpulse.features.device_health")
    parser.add_argument("--no-spark", action="store_true")
    args = parser.parse_args()

    compare_models(
        experiment_name=args.experiment_name,
        feature_table=args.feature_table,
        use_spark=not args.no_spark,
    )
