"""
FastAPI application entry point.

Registers all API routers and configures CORS for Angular frontend.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logging.info("AI Purchasing Agent backend starting up")
    yield
    logging.info("AI Purchasing Agent backend shutting down")


app = FastAPI(
    title="AI Purchasing Agent",
    description="Full-stack AI purchasing system with agent investigation, validation, and human approval.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import products, inventory, suppliers, purchase_orders, recommendations, dashboard, demo

# Register routers
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(suppliers.router)
app.include_router(purchase_orders.router)
app.include_router(recommendations.router)
app.include_router(dashboard.router)
app.include_router(demo.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "ai-purchasing-agent"}
