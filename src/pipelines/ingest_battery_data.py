"""
FleetPulse — Battery Data Ingestion Pipeline
=============================================
Ingests NASA Li-ion Battery Aging dataset (.mat files from PCoE repository),
maps battery IDs to synthetic enterprise device IDs, and writes to Delta table.

Usage (Databricks):
    dbutils.widgets.text("raw_data_path", "/Volumes/fleetpulse/raw/battery/")
    dbutils.widgets.text("output_table", "fleetpulse.raw.battery_cycles")

Usage (local/standalone):
    python -m src.pipelines.ingest_battery_data \
        --raw-data-path ./data/raw/battery/ \
        --output-path ./data/processed/battery_cycles/
"""

import argparse
import hashlib
import os
import random
from datetime import datetime, timedelta

import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Row

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# NASA PCoE dataset battery IDs and their test conditions
NASA_BATTERY_IDS = [
    "B0005", "B0006", "B0007", "B0018",
    "B0025", "B0026", "B0027", "B0028",
    "B0029", "B0030", "B0031", "B0032",
    "B0033", "B0034", "B0036",
    "B0038", "B0039", "B0040",
    "B0041", "B0042", "B0043", "B0044",
    "B0045", "B0046", "B0047", "B0048",
    "B0049", "B0050", "B0051", "B0052",
    "B0053", "B0054", "B0055", "B0056",
]

# Synthetic device models for mapping
DEVICE_MODELS = [
    ("iPhone 15 Pro", "Apple", "iOS"),
    ("iPhone 14", "Apple", "iOS"),
    ("iPhone 13", "Apple", "iOS"),
    ("Galaxy S24", "Samsung", "Android"),
    ("Galaxy S23", "Samsung", "Android"),
    ("Galaxy A54", "Samsung", "Android"),
    ("Pixel 8 Pro", "Google", "Android"),
    ("Pixel 7a", "Google", "Android"),
    ("Surface Pro 10", "Microsoft", "Windows"),
    ("ThinkPad X1 Carbon", "Lenovo", "Windows"),
]

# Fleet names for synthetic assignment
FLEET_NAMES = ["Sales", "Engineering", "Executive", "Support", "Marketing", "Operations"]


def _generate_device_id(battery_id: str, model_name: str) -> str:
    """Deterministic device ID from battery+model to ensure reproducibility."""
    seed = f"{battery_id}_{model_name}"
    hash_val = hashlib.sha256(seed.encode()).hexdigest()[:8]
    return f"DEV-{hash_val.upper()}"


def _map_batteries_to_devices(battery_ids: list[str]) -> list[dict]:
    """
    Map each NASA battery ID to a synthetic device with deterministic assignment.
    """
    random.seed(42)
    mappings = []
    for i, bid in enumerate(battery_ids):
        model_name, manufacturer, os_type = DEVICE_MODELS[i % len(DEVICE_MODELS)]
        fleet = FLEET_NAMES[i % len(FLEET_NAMES)]
        device_id = _generate_device_id(bid, model_name)
        mappings.append({
            "battery_id": bid,
            "device_id": device_id,
            "device_model": model_name,
            "manufacturer": manufacturer,
            "os_type": os_type,
            "fleet_name": fleet,
        })
    return mappings


def parse_mat_file(mat_path: str) -> list[dict]:
    """
    Parse a NASA PCoE .mat file and extract charge/discharge cycle data.

    The NASA dataset .mat files contain a struct with fields:
        - cycle: array of cycle structs
        - Each cycle has: type ('charge'/'discharge'), ambient_temperature,
          data (voltage_measured, current_measured, temperature_measured, time, capacity)

    Returns:
        List of dicts, each representing one cycle's summary data.
    """
    from scipy.io import loadmat

    mat = loadmat(mat_path, squeeze_me=True, struct_as_record=False)

    # The mat file has a top-level variable matching the battery ID
    battery_id = os.path.splitext(os.path.basename(mat_path))[0]

    # Navigate to the cycle data
    # Structure: mat[battery_id].cycle (array of cycle objects)
    try:
        battery_struct = mat[battery_id]
        cycles = battery_struct.cycle
    except (KeyError, AttributeError):
        # Try alternate structures found in some NASA files
        for key in mat:
            if not key.startswith("_"):
                battery_struct = mat[key]
                if hasattr(battery_struct, "cycle"):
                    cycles = battery_struct.cycle
                    break
        else:
            print(f"WARNING: Could not parse {mat_path} — skipping")
            return []

    if not hasattr(cycles, "__len__"):
        cycles = [cycles]

    rows = []
    base_time = datetime(2024, 1, 1)

    for idx, cycle in enumerate(cycles):
        try:
            cycle_type = str(cycle.type).strip().lower()
            ambient_temp = float(cycle.ambient_temperature) if hasattr(cycle, "ambient_temperature") else None

            data = cycle.data
            voltage = np.array(data.Voltage_measured, dtype=np.float32).tolist() if hasattr(data, "Voltage_measured") else None
            current = np.array(data.Current_measured, dtype=np.float32).tolist() if hasattr(data, "Current_measured") else None
            temperature = np.array(data.Temperature_measured, dtype=np.float32).tolist() if hasattr(data, "Temperature_measured") else None
            time_arr = np.array(data.Time, dtype=np.float32).tolist() if hasattr(data, "Time") else None

            # Capacity — some files have Capacity, others have Charge/Discharge_Capacity
            capacity = None
            for cap_field in ["Capacity", "Discharge_Capacity", "Charge_Capacity"]:
                if hasattr(data, cap_field):
                    cap_data = getattr(data, cap_field)
                    if hasattr(cap_data, "__len__") and len(cap_data) > 0:
                        capacity = float(np.max(np.abs(np.array(cap_data, dtype=np.float64))))
                    else:
                        capacity = float(cap_data)
                    break

            duration = float(time_arr[-1] - time_arr[0]) if time_arr and len(time_arr) > 1 else None

            # Truncate large arrays to summary (keep first/last 50 points for storage efficiency)
            def _truncate(arr, max_points=100):
                if arr is None or len(arr) <= max_points:
                    return arr
                half = max_points // 2
                return arr[:half] + arr[-half:]

            rows.append({
                "battery_id": battery_id,
                "cycle_number": idx + 1,
                "cycle_type": cycle_type,
                "ambient_temperature_c": ambient_temp,
                "voltage_measured_v": _truncate(voltage),
                "current_measured_a": _truncate(current),
                "temperature_measured_c": _truncate(temperature),
                "time_s": _truncate(time_arr),
                "capacity_ah": capacity,
                "cycle_duration_s": duration,
                "timestamp": base_time + timedelta(hours=idx * 2),  # ~2 hours per cycle
            })

        except Exception as e:
            print(f"WARNING: Error parsing cycle {idx} in {mat_path}: {e}")
            continue

    return rows


def generate_synthetic_battery_data(num_batteries: int = 34, cycles_per_battery: int = 168) -> list[dict]:
    """
    Generate synthetic battery degradation data matching NASA dataset characteristics
    when the actual .mat files are unavailable.

    Models realistic Li-ion aging:
        - Capacity starts at ~2.0 Ah (18650 cell) and degrades
        - Faster fade at higher temperatures
        - Internal resistance increases over cycles
        - Some batteries show sudden capacity drop ("knee point")
    """
    np.random.seed(42)
    base_time = datetime(2024, 1, 1)
    rows = []

    for i in range(min(num_batteries, len(NASA_BATTERY_IDS))):
        battery_id = NASA_BATTERY_IDS[i]
        nominal_capacity = 2.0 + np.random.uniform(-0.1, 0.1)
        ambient_temp = np.random.choice([24.0, 34.0, 43.0])  # NASA test conditions

        # Degradation parameters
        fade_rate = np.random.uniform(0.001, 0.004)  # Ah per cycle
        knee_point = np.random.randint(100, 160) if np.random.random() > 0.7 else None
        resistance_base = 0.02 + np.random.uniform(0, 0.01)

        current_capacity = nominal_capacity

        for cycle_num in range(1, cycles_per_battery + 1):
            # Simulate degradation
            noise = np.random.normal(0, 0.002)
            if knee_point and cycle_num > knee_point:
                fade = fade_rate * 2.5 + noise  # Accelerated fade after knee
            else:
                fade = fade_rate + noise

            current_capacity = max(0.5, current_capacity - abs(fade))
            resistance = resistance_base + (cycle_num * 0.0001) + np.random.normal(0, 0.001)

            # Generate time-series snippet for this cycle
            n_points = 50
            time_points = np.linspace(0, 3600, n_points).tolist()

            # Discharge voltage curve (simplified)
            voltage = (
                4.2 - (4.2 - 2.5) * np.linspace(0, 1, n_points) ** 0.8
                + np.random.normal(0, 0.01, n_points)
            ).tolist()

            current_vals = (
                np.full(n_points, -1.5) + np.random.normal(0, 0.02, n_points)
            ).tolist()

            temp_vals = (
                ambient_temp + np.linspace(0, 5, n_points) + np.random.normal(0, 0.3, n_points)
            ).tolist()

            for cycle_type in ["charge", "discharge"]:
                rows.append({
                    "battery_id": battery_id,
                    "cycle_number": cycle_num,
                    "cycle_type": cycle_type,
                    "ambient_temperature_c": float(ambient_temp),
                    "voltage_measured_v": voltage,
                    "current_measured_a": current_vals,
                    "temperature_measured_c": temp_vals,
                    "time_s": time_points,
                    "capacity_ah": float(current_capacity) if cycle_type == "discharge" else None,
                    "nominal_capacity_ah": float(nominal_capacity),
                    "internal_resistance_ohm": float(max(0.01, resistance)),
                    "cycle_duration_s": 3600.0,
                    "timestamp": base_time + timedelta(hours=(cycle_num - 1) * 4 + (0 if cycle_type == "charge" else 2)),
                })

    return rows


def run_ingestion(spark: SparkSession, raw_data_path: str, output_table: str, use_synthetic: bool = False):
    """
    Main ingestion pipeline. Reads .mat files or generates synthetic data,
    maps to device IDs, and writes to Delta.

    Args:
        spark: SparkSession
        raw_data_path: Path to directory containing .mat files
        output_table: Delta table name (e.g., "fleetpulse.raw.battery_cycles")
        use_synthetic: If True, generate synthetic data instead of parsing .mat files
    """
    device_map = _map_batteries_to_devices(NASA_BATTERY_IDS)
    device_lookup = {d["battery_id"]: d for d in device_map}

    # ── Collect cycle data ───────────────────────────────────────────────
    if use_synthetic:
        print("Generating synthetic battery data...")
        cycle_rows = generate_synthetic_battery_data()
    else:
        print(f"Reading .mat files from {raw_data_path}...")
        cycle_rows = []
        mat_files = [f for f in os.listdir(raw_data_path) if f.endswith(".mat")]
        if not mat_files:
            print(f"No .mat files found in {raw_data_path}. Falling back to synthetic data.")
            cycle_rows = generate_synthetic_battery_data()
        else:
            for fname in sorted(mat_files):
                fpath = os.path.join(raw_data_path, fname)
                print(f"  Parsing {fname}...")
                parsed = parse_mat_file(fpath)
                cycle_rows.extend(parsed)

    print(f"Total cycle records: {len(cycle_rows)}")

    # ── Enrich with device info ──────────────────────────────────────────
    now = datetime.utcnow()
    enriched_rows = []
    for row in cycle_rows:
        device_info = device_lookup.get(row["battery_id"])
        if not device_info:
            continue
        enriched_rows.append({
            **row,
            "device_id": device_info["device_id"],
            "device_model": device_info["device_model"],
            "nominal_capacity_ah": row.get("nominal_capacity_ah", 2.0),
            "ingestion_timestamp": now,
        })

    # ── Write to Delta ───────────────────────────────────────────────────
    df = spark.createDataFrame([Row(**r) for r in enriched_rows])

    # Ensure correct column order
    columns = [
        "device_id", "device_model", "battery_id", "cycle_number", "cycle_type",
        "ambient_temperature_c", "voltage_measured_v", "current_measured_a",
        "temperature_measured_c", "time_s", "capacity_ah", "nominal_capacity_ah",
        "internal_resistance_ohm", "cycle_duration_s", "timestamp", "ingestion_timestamp",
    ]
    df = df.select([c for c in columns if c in df.columns])

    print(f"Writing {df.count()} rows to {output_table}...")
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(output_table)
    print("Battery data ingestion complete.")

    # ── Also write device inventory ──────────────────────────────────────
    random.seed(42)
    inventory_rows = []
    os_versions = {"iOS": ["17.2", "17.1", "16.7"], "Android": ["14", "13", "12"], "Windows": ["11 23H2", "11 22H2", "10 22H2"]}
    latest_versions = {"iOS": "17.2", "Android": "14", "Windows": "11 23H2"}

    for dev in device_map:
        os_type = dev["os_type"]
        os_version = random.choice(os_versions[os_type])
        inventory_rows.append({
            "device_id": dev["device_id"],
            "device_model": dev["device_model"],
            "manufacturer": dev["manufacturer"],
            "os_type": os_type,
            "os_version": os_version,
            "latest_os_version": latest_versions[os_type],
            "fleet_name": dev["fleet_name"],
            "assigned_user": f"user_{dev['device_id'][-4:].lower()}@company.com",
            "enrollment_date": datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365)),
            "last_checkin": now - timedelta(hours=random.randint(1, 72)),
            "mdm_compliant": random.choice(["true", "true", "true", "false"]),
            "encryption_enabled": random.choice(["true", "true", "true", "false"]),
            "passcode_set": random.choice(["true", "true", "false"]),
        })

    inv_df = spark.createDataFrame([Row(**r) for r in inventory_rows])
    inv_table = output_table.rsplit(".", 1)[0] + ".device_inventory"
    inv_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(inv_table)
    print(f"Device inventory written to {inv_table}.")

    return df


# ==============================================================================
# CLI entrypoint
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetPulse Battery Data Ingestion")
    parser.add_argument("--raw-data-path", default="./data/raw/battery/", help="Path to .mat files")
    parser.add_argument("--output-table", default="fleetpulse.raw.battery_cycles", help="Delta table name")
    parser.add_argument("--output-path", default=None, help="Local path for Delta output (non-Databricks)")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data instead of .mat files")
    args = parser.parse_args()

    spark = (
        SparkSession.builder
        .appName("FleetPulse-BatteryIngestion")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )

    if args.output_path:
        # Local mode — write to path instead of table
        print(f"Running in local mode, output to {args.output_path}")
        run_ingestion(spark, args.raw_data_path, args.output_path, use_synthetic=args.synthetic)
    else:
        run_ingestion(spark, args.raw_data_path, args.output_table, use_synthetic=args.synthetic)
