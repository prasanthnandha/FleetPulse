"""
FleetPulse — Fleet Dashboard Data Routes
==========================================
REST endpoints for fleet overview, device list, and trend data.
"""

import random
from datetime import datetime, timedelta

import numpy as np
from fastapi import APIRouter, Query

from src.agent.tools.prediction_tool import PredictionTool
from src.api.models import DeviceHealth, FleetOverview, FleetTrendPoint, FleetTrendResponse

router = APIRouter(prefix="/fleet", tags=["fleet"])

# Shared prediction tool instance
_prediction_tool = PredictionTool()


@router.get("/overview", response_model=FleetOverview)
async def fleet_overview(fleet_name: str | None = None):
    """
    Get fleet-level risk overview with summary statistics.
    If fleet_name is provided, filters to that fleet only.
    """
    result = _prediction_tool.execute({
        "fleet_name": fleet_name,
        "time_horizon_days": 30,
    })

    devices = result.get("devices", [])
    risk_dist = result.get("risk_distribution", {})

    # Compute averages
    risk_scores = [d.get("overall_risk_score", 50) for d in devices]
    battery_scores = [d.get("battery_health_score", 50) for d in devices if d.get("battery_health_score") is not None]
    compliance_scores = [d.get("compliance_score", 50) for d in devices if d.get("compliance_score") is not None]

    needing_attention = sum(
        1 for d in devices
        if d.get("remaining_useful_life_days", 999) < 30
        or d.get("overall_risk_score", 0) > 70
    )

    # Build DeviceHealth objects for top risk devices
    top_devices = []
    for d in sorted(devices, key=lambda x: x.get("overall_risk_score", 0), reverse=True)[:5]:
        top_devices.append(DeviceHealth(
            device_id=d.get("device_id", ""),
            device_model=d.get("device_model", ""),
            fleet_name=d.get("fleet_name", ""),
            risk_tier=d.get("risk_tier", "healthy"),
            overall_risk_score=d.get("overall_risk_score", 0),
            battery_health_score=d.get("battery_health_score"),
            compliance_score=d.get("compliance_score"),
            remaining_useful_life_days=d.get("remaining_useful_life_days"),
            days_to_non_compliance=d.get("days_to_non_compliance"),
            capacity_fade_pct=d.get("capacity_fade_pct"),
            cycle_count=d.get("cycle_count"),
            days_since_last_patch=d.get("days_since_last_patch"),
            driving_factors=d.get("driving_factors", []),
        ))

    return FleetOverview(
        total_devices=len(devices),
        risk_distribution=risk_dist,
        avg_risk_score=round(np.mean(risk_scores), 1) if risk_scores else 0,
        avg_battery_health=round(np.mean(battery_scores), 1) if battery_scores else 0,
        avg_compliance_score=round(np.mean(compliance_scores), 1) if compliance_scores else 0,
        devices_needing_attention=needing_attention,
        top_risk_devices=top_devices,
    )


@router.get("/devices", response_model=list[DeviceHealth])
async def list_devices(
    fleet_name: str | None = None,
    risk_tier: str | None = None,
    sort_by: str = Query(default="overall_risk_score", regex="^(overall_risk_score|remaining_useful_life_days|compliance_score|battery_health_score)$"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List devices with health scores, optionally filtered and sorted."""
    result = _prediction_tool.execute({
        "fleet_name": fleet_name,
        "risk_tier_filter": risk_tier,
    })

    devices = result.get("devices", [])

    # Sort
    reverse = order == "desc"
    devices.sort(key=lambda d: d.get(sort_by, 0) or 0, reverse=reverse)

    # Paginate
    devices = devices[offset:offset + limit]

    return [
        DeviceHealth(
            device_id=d.get("device_id", ""),
            device_model=d.get("device_model", ""),
            fleet_name=d.get("fleet_name", ""),
            risk_tier=d.get("risk_tier", "healthy"),
            overall_risk_score=d.get("overall_risk_score", 0),
            battery_health_score=d.get("battery_health_score"),
            compliance_score=d.get("compliance_score"),
            remaining_useful_life_days=d.get("remaining_useful_life_days"),
            days_to_non_compliance=d.get("days_to_non_compliance"),
            capacity_fade_pct=d.get("capacity_fade_pct"),
            cycle_count=d.get("cycle_count"),
            days_since_last_patch=d.get("days_since_last_patch"),
            driving_factors=d.get("driving_factors", []),
        )
        for d in devices
    ]


@router.get("/device/{device_id}", response_model=DeviceHealth)
async def get_device(device_id: str):
    """Get detailed health info for a specific device."""
    result = _prediction_tool.execute({"device_id": device_id})
    devices = result.get("devices", [])

    if not devices:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    d = devices[0]
    return DeviceHealth(
        device_id=d.get("device_id", ""),
        device_model=d.get("device_model", ""),
        fleet_name=d.get("fleet_name", ""),
        risk_tier=d.get("risk_tier", "healthy"),
        overall_risk_score=d.get("overall_risk_score", 0),
        battery_health_score=d.get("battery_health_score"),
        compliance_score=d.get("compliance_score"),
        remaining_useful_life_days=d.get("remaining_useful_life_days"),
        days_to_non_compliance=d.get("days_to_non_compliance"),
        capacity_fade_pct=d.get("capacity_fade_pct"),
        cycle_count=d.get("cycle_count"),
        days_since_last_patch=d.get("days_since_last_patch"),
        driving_factors=d.get("driving_factors", []),
    )


@router.get("/trends", response_model=FleetTrendResponse)
async def fleet_trends(
    fleet_name: str | None = None,
    days: int = Query(default=30, ge=7, le=365),
):
    """
    Get fleet risk trend data over time.
    Returns synthetic trend data for development (real data would come from
    historical feature table snapshots).
    """
    random.seed(42)
    np.random.seed(42)

    trend_data = []
    base_risk = 45.0
    base_critical = 2
    base_warning = 5
    total_devices = 34

    for i in range(days):
        date = datetime.utcnow() - timedelta(days=days - i - 1)

        # Simulate gradual drift with noise
        drift = i * 0.1  # Slow upward trend
        noise = np.random.normal(0, 2)

        avg_risk = max(10, min(90, base_risk + drift + noise))
        critical = max(0, int(base_critical + drift * 0.05 + np.random.normal(0, 0.8)))
        warning = max(0, int(base_warning + drift * 0.08 + np.random.normal(0, 1)))

        trend_data.append(FleetTrendPoint(
            date=date.strftime("%Y-%m-%d"),
            avg_risk_score=round(avg_risk, 1),
            critical_count=critical,
            warning_count=warning,
            total_devices=total_devices,
        ))

    return FleetTrendResponse(
        fleet_name=fleet_name,
        trend_data=trend_data,
    )
