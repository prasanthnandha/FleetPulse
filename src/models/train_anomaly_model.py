"""
FleetPulse — Anomaly Detection Model Training
===============================================
Trains an Isolation Forest to flag sudden-drop anomalies in device health
(e.g., battery capacity cliff, unexpected compliance violation, possible
device compromise or misconfiguration).

Usage (Databricks):
    dbutils.widgets.text("feature_table", "fleetpulse.features.device_health")
    dbutils.widgets.text("experiment_name", "/FleetPulse/Anomaly-Detector")
    dbutils.widgets.text("model_name", "fleetpulse.models.anomaly_detector")

Usage (local):
    python -m src.models.train_anomaly_model --feature-table ./data/processed/device_health/
"""

import argparse
from datetime import datetime

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


# ==============================================================================
# Feature Configuration
# ==============================================================================

# Features most indicative of anomalous behavior
ANOMALY_FEATURES = [
    "capacity_fade_pct",
    "capacity_fade_rate",
    "voltage_drop_rate",
    "internal_resistance_trend",
    "avg_temperature_exposure_c",
    "max_temperature_c",
    "cycle_count",
    "overall_risk_score",
    "battery_health_score",
    "compliance_score",
    "days_since_last_patch",
    "os_version_lag",
    "unpatched_critical_cves",
]


def prepare_anomaly_data(feature_df: pd.DataFrame):
    """
    Prepare data for anomaly detection.

    Since Isolation Forest is unsupervised, we don't need labels.
    However, we generate synthetic "known anomaly" labels for evaluation
    based on domain rules (e.g., sudden capacity cliff, extreme values).
    """
    available_features = [c for c in ANOMALY_FEATURES if c in feature_df.columns]
    df = feature_df[available_features].fillna(0).astype(np.float32)

    # Generate heuristic anomaly labels for evaluation
    # These represent "ground truth" based on domain knowledge
    labels = np.ones(len(df))  # 1 = normal

    if "capacity_fade_rate" in df.columns:
        # Sudden capacity cliff: fade rate > 3 standard deviations
        mean_rate = df["capacity_fade_rate"].mean()
        std_rate = df["capacity_fade_rate"].std()
        if std_rate > 0:
            labels[df["capacity_fade_rate"] < mean_rate - 3 * std_rate] = -1

    if "overall_risk_score" in df.columns:
        # Extreme risk: score > 90
        labels[df["overall_risk_score"] > 90] = -1

    if "voltage_drop_rate" in df.columns:
        # Abnormal voltage drop
        mean_vdr = df["voltage_drop_rate"].mean()
        std_vdr = df["voltage_drop_rate"].std()
        if std_vdr > 0:
            labels[df["voltage_drop_rate"] < mean_vdr - 3 * std_vdr] = -1

    if "internal_resistance_trend" in df.columns:
        # Rapid resistance increase (possible internal damage)
        mean_irt = df["internal_resistance_trend"].mean()
        std_irt = df["internal_resistance_trend"].std()
        if std_irt > 0:
            labels[df["internal_resistance_trend"] > mean_irt + 3 * std_irt] = -1

    anomaly_count = (labels == -1).sum()
    print(f"Heuristic anomaly labels: {anomaly_count} anomalies out of {len(labels)} devices "
          f"({anomaly_count / len(labels) * 100:.1f}%)")

    return df, labels, available_features


def train_isolation_forest(
    feature_df: pd.DataFrame,
    experiment_name: str = "/FleetPulse/Anomaly-Detector",
    model_name: str | None = "fleetpulse.models.anomaly_detector",
    hyperparams: dict | None = None,
) -> dict:
    """
    Train an Isolation Forest model with MLflow tracking.
    """
    X, heuristic_labels, feature_names = prepare_anomaly_data(feature_df)

    # Default hyperparameters
    params = {
        "n_estimators": 200,
        "max_samples": "auto",
        "contamination": 0.05,  # Expected ~5% anomaly rate
        "max_features": 1.0,
        "bootstrap": True,
        "random_state": 42,
        "n_jobs": -1,
    }
    if hyperparams:
        params.update(hyperparams)

    # Standardize features
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X),
        columns=feature_names,
        index=X.index,
    )

    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"iforest_{datetime.now().strftime('%Y%m%d_%H%M')}") as run:
        # Log parameters
        mlflow.log_params(params)
        mlflow.log_param("num_features", len(feature_names))
        mlflow.log_param("num_samples", len(X_scaled))
        mlflow.log_param("feature_names", json.dumps(feature_names))

        # Train model
        model = IsolationForest(**params)
        model.fit(X_scaled)

        # Predict
        predictions = model.predict(X_scaled)  # 1 = normal, -1 = anomaly
        anomaly_scores = model.decision_function(X_scaled)  # Lower = more anomalous

        # ── Metrics against heuristic labels ─────────────────────────────
        n_anomalies_detected = (predictions == -1).sum()
        n_heuristic_anomalies = (heuristic_labels == -1).sum()

        metrics = {
            "num_anomalies_detected": int(n_anomalies_detected),
            "anomaly_rate": float(n_anomalies_detected / len(predictions)),
            "mean_anomaly_score": float(anomaly_scores.mean()),
            "std_anomaly_score": float(anomaly_scores.std()),
        }

        # If we have heuristic labels, compute precision/recall
        if n_heuristic_anomalies > 0:
            # Convert to binary: 0 = normal, 1 = anomaly
            pred_binary = (predictions == -1).astype(int)
            true_binary = (heuristic_labels == -1).astype(int)

            precision, recall, f1, _ = precision_recall_fscore_support(
                true_binary, pred_binary, average="binary", zero_division=0,
            )
            metrics.update({
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
            })

            try:
                auc = roc_auc_score(true_binary, -anomaly_scores)  # Negate: higher score = more normal
                metrics["roc_auc"] = float(auc)
            except ValueError:
                pass

        mlflow.log_metrics(metrics)

        # Feature importance (via permutation-like approach)
        # Isolation Forest doesn't have native feature_importances_,
        # so we use the average path length contribution
        importance = {}
        baseline_score = anomaly_scores.mean()
        for i, fname in enumerate(feature_names):
            X_permuted = X_scaled.copy()
            X_permuted.iloc[:, i] = np.random.permutation(X_permuted.iloc[:, i].values)
            permuted_scores = model.decision_function(X_permuted)
            importance[fname] = float(abs(permuted_scores.mean() - baseline_score))

        sorted_importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        mlflow.log_dict(sorted_importance, "feature_importance.json")

        # Log model (with scaler as part of the artifact)
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            input_example=X_scaled.head(3),
        )

        # Also log the scaler
        mlflow.sklearn.log_model(scaler, artifact_path="scaler")

        # Register model
        if model_name:
            model_uri = f"runs:/{run.info.run_id}/model"
            try:
                mv = mlflow.register_model(model_uri, model_name)
                mlflow.log_param("registered_model_version", mv.version)
                print(f"Model registered: {model_name} v{mv.version}")
            except Exception as e:
                print(f"Model registration skipped: {e}")

        print(f"\n{'='*60}")
        print(f"Isolation Forest Training Complete")
        print(f"Run ID: {run.info.run_id}")
        print(f"Anomalies detected: {n_anomalies_detected}/{len(predictions)} "
              f"({n_anomalies_detected/len(predictions)*100:.1f}%)")
        if "f1_score" in metrics:
            print(f"Precision: {metrics['precision']:.4f}")
            print(f"Recall:    {metrics['recall']:.4f}")
            print(f"F1:        {metrics['f1_score']:.4f}")
        print(f"Top features: {list(sorted_importance.keys())[:5]}")
        print(f"{'='*60}\n")

        return {
            "model": model,
            "scaler": scaler,
            "metrics": metrics,
            "feature_importance": sorted_importance,
            "run_id": run.info.run_id,
            "feature_names": feature_names,
        }


# Need json import for feature_names logging
import json


def run_training(
    feature_table: str,
    experiment_name: str = "/FleetPulse/Anomaly-Detector",
    model_name: str | None = "fleetpulse.models.anomaly_detector",
    use_spark: bool = True,
):
    """Main training pipeline."""
    if use_spark:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName("FleetPulse-AnomalyTraining").getOrCreate()
        if "." in feature_table:
            df = spark.table(feature_table).toPandas()
        else:
            df = spark.read.format("delta").load(feature_table).toPandas()
    else:
        if feature_table.endswith(".csv"):
            df = pd.read_csv(feature_table)
        else:
            df = pd.read_parquet(feature_table)

    print(f"Loaded {len(df)} records from {feature_table}")

    result = train_isolation_forest(
        df,
        experiment_name=experiment_name,
        model_name=model_name,
    )

    return result


# ==============================================================================
# CLI entrypoint
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse Anomaly Model Training")
    parser.add_argument("--feature-table", default="fleetpulse.features.device_health")
    parser.add_argument("--experiment-name", default="/FleetPulse/Anomaly-Detector")
    parser.add_argument("--model-name", default="fleetpulse.models.anomaly_detector")
    parser.add_argument("--no-spark", action="store_true")
    args = parser.parse_args()

    run_training(
        feature_table=args.feature_table,
        experiment_name=args.experiment_name,
        model_name=args.model_name,
        use_spark=not args.no_spark,
    )
