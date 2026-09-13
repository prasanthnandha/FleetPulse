"""
FleetPulse — Remaining Useful Life (RUL) Model Training
========================================================
Trains a gradient-boosted regressor (XGBoost or LightGBM) to predict:
    1. remaining_useful_life_days (battery)
    2. days_to_non_compliance

Tracks experiments with MLflow and registers the best model to the
Unity Catalog Model Registry.

Usage (Databricks):
    dbutils.widgets.text("feature_table", "fleetpulse.features.device_health")
    dbutils.widgets.text("experiment_name", "/FleetPulse/RUL-Predictor")
    dbutils.widgets.text("model_name", "fleetpulse.models.rul_predictor")

Usage (local):
    python -m src.models.train_rul_model --feature-table ./data/processed/device_health/
"""

import argparse
from datetime import datetime

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# ==============================================================================
# Feature Configuration
# ==============================================================================

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

TARGET_COLUMNS = [
    "remaining_useful_life_days",
    "days_to_non_compliance",
]


def prepare_data(feature_df: pd.DataFrame, target_col: str, test_size: float = 0.2):
    """
    Prepare train/test split with time-aware splitting to prevent leakage.

    Instead of random splitting, we use the last `test_size` fraction of data
    ordered by snapshot_date as the test set.
    """
    # Sort by snapshot date for time-aware split
    if "snapshot_date" in feature_df.columns:
        feature_df = feature_df.sort_values("snapshot_date")

    # Drop rows where target is missing
    df = feature_df.dropna(subset=[target_col])

    # Feature matrix
    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[available_features].fillna(0).astype(np.float32)
    y = df[target_col].astype(np.float32)

    # Time-aware split
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    return X_train, X_test, y_train, y_test, available_features


def train_xgboost_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: list[str],
    target_name: str,
    experiment_name: str,
    model_name: str | None = None,
    hyperparams: dict | None = None,
) -> dict:
    """
    Train an XGBoost regressor with MLflow tracking.

    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data
        feature_names: List of feature column names
        target_name: Name of the target variable
        experiment_name: MLflow experiment name
        model_name: Model registry name (if None, don't register)
        hyperparams: Optional hyperparameter overrides

    Returns:
        Dict with model, metrics, and run info
    """
    # Default hyperparameters tuned for battery degradation prediction
    params = {
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.05,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "early_stopping_rounds": 50,
        "random_state": 42,
        "n_jobs": -1,
    }
    if hyperparams:
        params.update(hyperparams)

    # Pop early_stopping_rounds to prevent it being passed to XGBoost constructor
    params.pop("early_stopping_rounds", 50)

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"xgboost_{target_name}_{datetime.now().strftime('%Y%m%d_%H%M')}") as run:
        # Log parameters
        mlflow.log_params(params)
        mlflow.log_param("target_variable", target_name)
        mlflow.log_param("num_features", len(feature_names))
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("test_size", len(X_test))

        # Train model
        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=50,
        )

        # Predict
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)

        # Metrics
        train_metrics = {
            "train_rmse": float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
            "train_mae": float(mean_absolute_error(y_train, y_pred_train)),
            "train_r2": float(r2_score(y_train, y_pred_train)),
        }
        test_metrics = {
            "test_rmse": float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
            "test_mae": float(mean_absolute_error(y_test, y_pred_test)),
            "test_r2": float(r2_score(y_test, y_pred_test)),
        }

        # Cross-validation score
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = cross_val_score(
            xgb.XGBRegressor(**params),
            pd.concat([X_train, X_test]),
            pd.concat([y_train, y_test]),
            cv=tscv,
            scoring="neg_mean_squared_error",
        )
        cv_rmse = float(np.sqrt(-cv_scores.mean()))

        all_metrics = {**train_metrics, **test_metrics, "cv_rmse": cv_rmse}
        mlflow.log_metrics(all_metrics)

        # Feature importance
        importance = dict(zip(feature_names, model.feature_importances_.tolist()))
        sorted_importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        mlflow.log_dict(sorted_importance, "feature_importance.json")

        # Log top 5 features as parameters for easy comparison
        for i, (feat, imp) in enumerate(list(sorted_importance.items())[:5]):
            mlflow.log_metric(f"importance_top{i + 1}_{feat}", imp)

        # Log model
        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            input_example=X_test.head(3),
        )

        # Register model if name provided
        if model_name:
            model_uri = f"runs:/{run.info.run_id}/model"
            try:
                mv = mlflow.register_model(model_uri, model_name)
                mlflow.log_param("registered_model_version", mv.version)
                print(f"Model registered: {model_name} v{mv.version}")
            except Exception as e:
                print(f"Model registration skipped (may need Unity Catalog): {e}")

        print(f"\n{'=' * 60}")
        print(f"Target: {target_name}")
        print(f"Run ID: {run.info.run_id}")
        print(f"Test RMSE: {test_metrics['test_rmse']:.4f}")
        print(f"Test MAE:  {test_metrics['test_mae']:.4f}")
        print(f"Test R²:   {test_metrics['test_r2']:.4f}")
        print(f"CV RMSE:   {cv_rmse:.4f}")
        print(f"Top features: {list(sorted_importance.keys())[:5]}")
        print(f"{'=' * 60}\n")

        return {
            "model": model,
            "metrics": all_metrics,
            "feature_importance": sorted_importance,
            "run_id": run.info.run_id,
            "feature_names": feature_names,
        }


def run_training(
    feature_table: str,
    experiment_name: str = "/FleetPulse/RUL-Predictor",
    model_name: str | None = "fleetpulse.models.rul_predictor",
    use_spark: bool = True,
):
    """
    Main training pipeline. Reads features, trains models for both targets.
    """
    # ── Load feature data ────────────────────────────────────────────────
    if use_spark:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("FleetPulse-RULTraining").getOrCreate()
        if "." in feature_table:
            df = spark.table(feature_table).toPandas()
        else:
            df = spark.read.format("delta").load(feature_table).toPandas()
    else:
        # Local CSV/parquet fallback
        if feature_table.endswith(".csv"):
            df = pd.read_csv(feature_table)
        else:
            df = pd.read_parquet(feature_table)

    print(f"Loaded {len(df)} records from {feature_table}")
    print(f"Columns: {list(df.columns)}")

    results = {}

    # ── Train RUL predictor ──────────────────────────────────────────────
    for target in TARGET_COLUMNS:
        if target not in df.columns:
            print(f"Skipping {target} — column not found")
            continue

        print(f"\n{'=' * 60}")
        print(f"Training model for: {target}")
        print(f"{'=' * 60}")

        X_train, X_test, y_train, y_test, features = prepare_data(df, target)

        if len(X_train) < 10:
            print(f"WARNING: Only {len(X_train)} training samples — skipping {target}")
            continue

        result = train_xgboost_model(
            X_train,
            y_train,
            X_test,
            y_test,
            feature_names=features,
            target_name=target,
            experiment_name=experiment_name,
            model_name=model_name if target == "remaining_useful_life_days" else None,
        )
        results[target] = result

    return results


# ==============================================================================
# CLI entrypoint
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse RUL Model Training")
    parser.add_argument("--feature-table", default="fleetpulse.features.device_health")
    parser.add_argument("--experiment-name", default="/FleetPulse/RUL-Predictor")
    parser.add_argument("--model-name", default="fleetpulse.models.rul_predictor")
    parser.add_argument("--no-spark", action="store_true", help="Load data without Spark")
    args = parser.parse_args()

    run_training(
        feature_table=args.feature_table,
        experiment_name=args.experiment_name,
        model_name=args.model_name,
        use_spark=not args.no_spark,
    )
