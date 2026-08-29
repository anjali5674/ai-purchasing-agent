"""
Demo Scenarios API — Safely apply deterministic purchasing scenarios to PostgreSQL.

Provides predefined test/demo scenarios that update live database state so the AI
agent investigates real changed data and generates data-driven decisions during demos.
"""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import (
    Product, FulfillmentNode, Inventory, DemandForecast,
    Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderStatus,
    Budget, PurchasingRecommendation, RecommendationStatus,
    AgentDecision, AgentActivityLog,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/demo", tags=["Demo Scenarios"])

SCENARIOS = [
    {
        "id": "normal_replenishment",
        "name": "Scenario A — Normal Purchase",
        "description": "Healthy budget ($50k) and storage (2000 capacity). Net need is 180 units (500 demand - 120 stock - 200 open PO). Agent recommends 180 units.",
        "expected_behavior": "MODIFY to 180 units, flags for human approval (>30% adjustment), passes all validation checks upon approval.",
    },
    {
        "id": "storage_constraint",
        "name": "Scenario B — Storage Capacity Constraint",
        "description": "Fulfillment Node storage capacity reduced to 400 with 350 existing units. Remaining capacity is only 50 units.",
        "expected_behavior": "Agent detects physical storage limitation and caps order at <= 50 units or flags storage risk.",
    },
    {
        "id": "supplier_constraint",
        "name": "Scenario C — Supplier Availability & Alternatives",
        "description": "Primary supplier has only 80 units in stock. Alternative supplier 'FreshDirect LATAM' has 1,500 units available.",
        "expected_behavior": "Agent investigates supplier constraints and identifies alternative suppliers or adjusts quantity.",
    },
    {
        "id": "budget_constraint",
        "name": "Scenario D — Budget Constraint",
        "description": "Fulfillment Node budget reduced to $500.00. Requested order of 300 units @ $11.00 ($3,300.00) exceeds budget.",
        "expected_behavior": "Agent detects financial limitation and suggests reduced quantity (<= 45 units) or rejects purchase.",
    },
]


@router.get("/scenarios")
def list_scenarios():
    """List available demo scenarios."""
    return SCENARIOS


@router.post("/scenarios/{scenario_id}")
def apply_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """Apply a predefined scenario by updating the live PostgreSQL database."""
    # Ensure Product 1, Node 1, Supplier 1 exist
    product = db.query(Product).filter(Product.id == 1).first()
    node = db.query(FulfillmentNode).filter(FulfillmentNode.id == 1).first()
    supplier1 = db.query(Supplier).filter(Supplier.id == 1).first()
    supplier3 = db.query(Supplier).filter(Supplier.id == 3).first()
    budget = db.query(Budget).filter(Budget.node_id == 1).first()
    inv = db.query(Inventory).filter(Inventory.product_id == 1, Inventory.node_id == 1).first()
    forecast = db.query(DemandForecast).filter(DemandForecast.product_id == 1, DemandForecast.node_id == 1).first()

    rec = db.query(PurchasingRecommendation).filter(PurchasingRecommendation.id == 1).first()
    if not rec:
        rec = PurchasingRecommendation(id=1, product_id=1, node_id=1, supplier_id=1, recommended_quantity=800)
        db.add(rec)

    # Clear previous decisions and logs for clean scenario demo
    db.query(AgentDecision).filter(AgentDecision.recommendation_id == 1).delete()
    db.query(AgentActivityLog).filter(AgentActivityLog.recommendation_id == 1).delete()

    if scenario_id == "normal_replenishment":
        # Scenario A: Healthy baseline
        db.query(PurchaseOrder).filter(PurchaseOrder.product_id == 1, PurchaseOrder.id != 1).delete()
        po1 = db.query(PurchaseOrder).filter(PurchaseOrder.id == 1).first()
        if po1:
            po1.status = PurchaseOrderStatus.OPEN
            po1.quantity = 200
        if node:
            node.storage_capacity = 2000
        if budget:
            budget.available_amount = 50000.00
        if supplier1:
            supplier1.available_quantity = 2000
            supplier1.minimum_order_quantity = 100
            supplier1.reliability_score = 0.95
        if inv:
            inv.current_quantity = 120
        if forecast:
            forecast.forecast_quantity = 500
        rec.recommended_quantity = 800
        rec.status = RecommendationStatus.PENDING

    elif scenario_id == "storage_constraint":
        # Scenario B: Storage capacity constrained to 400
        if node:
            node.storage_capacity = 400
        if budget:
            budget.available_amount = 50000.00
        if inv:
            inv.current_quantity = 250
        if supplier1:
            supplier1.available_quantity = 2000
            supplier1.minimum_order_quantity = 50
        if forecast:
            forecast.forecast_quantity = 500
        rec.recommended_quantity = 400
        rec.status = RecommendationStatus.PENDING

    elif scenario_id == "supplier_constraint":
        # Scenario C: Primary supplier stock low (80 units), alternative has 1500
        if node:
            node.storage_capacity = 2000
        if budget:
            budget.available_amount = 50000.00
        if supplier1:
            supplier1.available_quantity = 80  # Low stock
            supplier1.minimum_order_quantity = 50
        if supplier3:
            supplier3.available_quantity = 1500  # Alternative available
        if inv:
            inv.current_quantity = 100
        if forecast:
            forecast.forecast_quantity = 400
        rec.recommended_quantity = 300
        rec.status = RecommendationStatus.PENDING

    elif scenario_id == "budget_constraint":
        # Scenario D: Node budget strictly constrained to $500
        if node:
            node.storage_capacity = 2000
        if budget:
            budget.available_amount = 500.00  # Budget tight
        if supplier1:
            supplier1.available_quantity = 2000
            supplier1.minimum_order_quantity = 20
        if inv:
            inv.current_quantity = 50
        if forecast:
            forecast.forecast_quantity = 350
        rec.recommended_quantity = 300
        rec.status = RecommendationStatus.PENDING

    else:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    db.commit()
    logger.info(f"Applied demo scenario: {scenario_id}")

    return {
        "message": f"Scenario '{scenario_id}' applied to live database.",
        "scenario_id": scenario_id,
        "recommendation_id": 1,
        "status": "PENDING",
    }
