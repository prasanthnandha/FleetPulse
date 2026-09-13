# Databricks notebook source
# MAGIC %md
# MAGIC # FleetPulse — 02: Model Training & MLflow Experiment Tracking
# MAGIC
# MAGIC This notebook trains and logs:
# MAGIC 1. **RUL Predictor**: XGBoost regressor predicting remaining useful battery life
# MAGIC 2. **Anomaly Detector**: Isolation Forest identifying sudden hardware/compliance cliffs
# MAGIC 3. Logs metrics (RMSE, MAE, R²) and registers models to Unity Catalog

# COMMAND ----------

import mlflow
import mlflow.xgboost
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
from sklearn.ensemble import IsolationForest

# COMMAND ----------

dbutils.widgets.text("catalog", "fleetpulse", "Unity Catalog Name")
dbutils.widgets.text("schema", "dev", "Database Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

mlflow.set_experiment(f"/Users/{spark.sql('SELECT current_user()').collect()[0][0]}/fleetpulse-training")

# COMMAND ----------

# Load feature dataset from Delta Lake
features_df = spark.table(f"{catalog}.{schema}.device_health").toPandas()
print(f"Loaded {len(features_df)} device health records")

# COMMAND ----------

# Train XGBoost RUL Model
feature_cols = [
    "cycle_count", "current_capacity_ah", "nominal_capacity_ah",
    "capacity_fade_pct", "capacity_fade_rate", "avg_temperature_exposure_c",
    "max_temperature_c", "voltage_drop_rate", "internal_resistance_trend",
    "days_since_last_patch", "os_version_lag", "unpatched_critical_cves",
]

X = features_df[feature_cols].fillna(0)
y_rul = features_df["remaining_useful_life_days"]

X_train, X_test, y_train, y_test = train_test_split(X, y_rul, test_size=0.2, random_state=42)

with mlflow.start_run(run_name="xgboost_rul_regressor") as run:
    params = {
        "n_estimators": 150,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "random_state": 42,
    }
    mlflow.log_params(params)

    model = xgb.XGBRegressor(**params)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("r2", r2)

    mlflow.xgboost.log_model(
        model,
        artifact_path="model",
        registered_model_name=f"{catalog}.{schema}.rul_predictor"
    )
    print(f"RUL Model trained: RMSE={rmse:.2f}, MAE={mae:.2f}, R2={r2:.3f}")
