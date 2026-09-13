# Databricks notebook source
# MAGIC %md
# MAGIC # FleetPulse — 03: RAG Retrieval & Guardrail Demo
# MAGIC
# MAGIC This notebook demonstrates:
# MAGIC 1. Querying the Vector Search index for device parts and repair procedures
# MAGIC 2. Testing the **Confidence Threshold Guardrail** (threshold = 0.75)
# MAGIC 3. Verification of hallucination prevention for unknown devices

# COMMAND ----------

from src.rag.retriever import FleetPulseRetriever

# Initialize retriever (local or Databricks Vector Search)
retriever = FleetPulseRetriever(
    confidence_threshold=0.75,
    use_databricks=False,  # Set to True on Databricks workspace
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Query 1: High-Confidence Match (iPhone 13 Battery)

# COMMAND ----------

result_high = retriever.get_device_repair_info(
    device_model="iPhone 13",
    predicted_failure_component="battery"
)

print(f"Match Found: {result_high['found']}")
print(f"Confidence Score: {result_high['confidence']}")
print(f"Part Info: {result_high['part_info']}")
print(f"Estimated Repair Time: {result_high['estimated_repair_time_hours']} hours")
print("\nRepair Procedure Snippet:\n", result_high.get("repair_procedure", "")[:300])

# COMMAND ----------

# MAGIC %md
# MAGIC ### Query 2: Guardrail Triggered (Unknown / Non-Existent Device)

# COMMAND ----------

result_low = retriever.get_device_repair_info(
    device_model="Prototype NonExistent 2099",
    predicted_failure_component="quantum_warp_drive"
)

print(f"Match Found: {result_low['found']}")
print(f"Confidence Score: {result_low['confidence']}")
print(f"Guardrail Message:\n{result_low['message']}")
