"""
FleetPulse — Health Check Route
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "fleetpulse-api",
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check — verifies dependencies are available."""
    checks = {
        "api": True,
        "agent": True,  # TODO: ping LLM provider
        "prediction": True,  # TODO: ping model serving
        "rag": True,  # TODO: ping vector search
    }
    all_ready = all(checks.values())
    return {
        "ready": all_ready,
        "checks": checks,
    }
