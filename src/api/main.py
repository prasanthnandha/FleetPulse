"""
FleetPulse — FastAPI Application
==================================
Main API server that serves the agent, fleet data, and chat endpoints.

Usage:
    uvicorn src.api.main:app --reload --port 8000
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes.chat import router as chat_router
from src.api.routes.fleet import router as fleet_router
from src.api.routes.health import router as health_router

load_dotenv()

app = FastAPI(
    title="FleetPulse API",
    description="Agentic MDM system — predictive device health, RAG-powered repair info, and conversational IT ops assistant.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────────

app.include_router(health_router, prefix="/api")
app.include_router(fleet_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


# ── Static UI Serving (when built for production) ────────────────────────
ui_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "dist")
if os.path.exists(ui_dist_path):
    app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")
else:
    @app.get("/")
    async def root():
        return {
            "service": "FleetPulse API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/health",
        }


# ── Startup event ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print("FleetPulse API starting...")
    print(f"  CORS origins: {cors_origins}")
    print(f"  LLM provider: {os.getenv('LLM_PROVIDER', 'databricks')}")
    print(f"  Databricks host: {os.getenv('DATABRICKS_HOST', 'not configured')}")
    print("FleetPulse API ready.")
