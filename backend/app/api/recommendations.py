"""
Recommendations API — List, detail, agent review, and approval endpoints.

This is the central API for the purchasing workflow:
  GET  /recommendations          — list all
  GET  /recommendations/{id}     — detail with decisions + activity log
  POST /agent/review/{id}        — trigger AI agent investigation
  GET  /agent/activity/{id}      — get agent activity log
  POST /recommendations/{id}/approve  — human approves
  POST /recommendations/{id}/reject   — human rejects
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models.models import (
    PurchasingRecommendation, RecommendationStatus,
    AgentActivityLog, AgentDecision,
    PurchaseOrder, PurchaseOrderStatus,
    SupplierProduct,
)
from app.schemas.schemas import (
    RecommendationResponse, RecommendationListResponse,
    AgentActivityLogResponse, AgentReviewRequest, AgentReviewResponse,
)
from app.agent.orchestrator import review_recommendation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recommendations"])


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@router.get("/api/recommendations", response_model=list[RecommendationListResponse])
def list_recommendations(db: Session = Depends(get_db)):
    return (
        db.query(PurchasingRecommendation)
        .options(
            joinedload(PurchasingRecommendation.product),
            joinedload(PurchasingRecommendation.node),
        )
        .order_by(PurchasingRecommendation.created_at.desc())
        .all()
    )


@router.get("/api/recommendations/{rec_id}", response_model=RecommendationResponse)
def get_recommendation(rec_id: int, db: Session = Depends(get_db)):
    rec = (
        db.query(PurchasingRecommendation)
        .options(
            joinedload(PurchasingRecommendation.product),
            joinedload(PurchasingRecommendation.node),
            joinedload(PurchasingRecommendation.decisions),
            joinedload(PurchasingRecommendation.activity_logs),
        )
        .filter(PurchasingRecommendation.id == rec_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")
    return rec


@router.get("/api/recommendations/{rec_id}/context")
def get_recommendation_context(rec_id: int, db: Session = Depends(get_db)):
    """Aggregate all related data for the recommendation detail page.

    Returns inventory, demand forecast, open POs, supplier info, budget, and
    storage capacity — exactly what the agent investigates.
    """
    from app.models.models import (
        Inventory, DemandForecast, Supplier, Budget, FulfillmentNode,
    )

    rec = db.query(PurchasingRecommendation).filter(PurchasingRecommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")

    # Inventory
    inv = db.query(Inventory).filter(
        Inventory.product_id == rec.product_id,
        Inventory.node_id == rec.node_id,
    ).first()

    # Demand forecast
    forecast = db.query(DemandForecast).filter(
        DemandForecast.product_id == rec.product_id,
        DemandForecast.node_id == rec.node_id,
    ).first()

    # Open POs for same product + node
    open_pos = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.product_id == rec.product_id,
            PurchaseOrder.node_id == rec.node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        )
        .all()
    )
    open_po_total = sum(po.quantity for po in open_pos)

    # Supplier
    supplier = None
    supplier_price = None
    if rec.supplier_id:
        supplier = db.query(Supplier).filter(Supplier.id == rec.supplier_id).first()
        sp = db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == rec.supplier_id,
            SupplierProduct.product_id == rec.product_id,
        ).first()
        supplier_price = sp.unit_price if sp else None

    # Budget
    budget = db.query(Budget).filter(Budget.node_id == rec.node_id).first()
    committed_spend = sum(
        po.total_price for po in
        db.query(PurchaseOrder).filter(
            PurchaseOrder.node_id == rec.node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        ).all()
    )

    # Storage
    node = db.query(FulfillmentNode).filter(FulfillmentNode.id == rec.node_id).first()
    total_inventory_at_node = sum(
        i.current_quantity for i in
        db.query(Inventory).filter(Inventory.node_id == rec.node_id).all()
    )
    incoming_qty = sum(
        po.quantity for po in
        db.query(PurchaseOrder).filter(
            PurchaseOrder.node_id == rec.node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        ).all()
    )

    return {
        "inventory": {
            "current_quantity": inv.current_quantity if inv else 0,
        },
        "demand": {
            "forecast_quantity": forecast.forecast_quantity if forecast else 0,
            "forecast_period": forecast.forecast_period if forecast else None,
        },
        "open_purchase_orders": {
            "count": len(open_pos),
            "total_quantity": open_po_total,
            "orders": [
                {"id": po.id, "quantity": po.quantity, "status": po.status.value}
                for po in open_pos
            ],
        },
        "supplier": {
            "id": supplier.id if supplier else None,
            "name": supplier.name if supplier else None,
            "lead_time_days": supplier.lead_time_days if supplier else None,
            "minimum_order_quantity": supplier.minimum_order_quantity if supplier else None,
            "available_quantity": supplier.available_quantity if supplier else None,
            "reliability_score": supplier.reliability_score if supplier else None,
            "unit_price": supplier_price,
        } if supplier else None,
        "budget": {
            "total_budget": budget.available_amount if budget else 0,
            "committed_spend": committed_spend,
            "remaining": (budget.available_amount - committed_spend) if budget else 0,
        },
        "storage": {
            "total_capacity": node.storage_capacity if node else 0,
            "current_usage": total_inventory_at_node,
            "incoming": incoming_qty,
            "remaining": (node.storage_capacity - total_inventory_at_node - incoming_qty) if node else 0,
        },
    }



# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@router.post("/api/agent/review/{rec_id}")
def agent_review(rec_id: int, body: AgentReviewRequest | None = None, db: Session = Depends(get_db)):
    """Trigger the AI agent to investigate and review a recommendation."""
    rec = db.query(PurchasingRecommendation).filter(PurchasingRecommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")

    try:
        context = body.context if body else None
        result = review_recommendation(db, rec_id, context=context)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Agent review failed for recommendation {rec_id}: {e}")
        # Reset status so recommendation is not stuck in UNDER_REVIEW
        rec.status = RecommendationStatus.PENDING
        # Log the failure as an activity event
        db.add(AgentActivityLog(
            recommendation_id=rec_id,
            event_type="agent_error",
            event_data={"error": str(e)},
            timestamp=datetime.now(timezone.utc),
        ))
        db.commit()
        raise HTTPException(status_code=500, detail=f"Agent review failed: {str(e)}")


@router.get("/api/agent/activity/{rec_id}", response_model=list[AgentActivityLogResponse])
def get_agent_activity(rec_id: int, db: Session = Depends(get_db)):
    """Get the agent's activity log for a recommendation."""
    logs = (
        db.query(AgentActivityLog)
        .filter(AgentActivityLog.recommendation_id == rec_id)
        .order_by(AgentActivityLog.timestamp)
        .all()
    )
    return logs


# ---------------------------------------------------------------------------
# Human Approval
# ---------------------------------------------------------------------------

@router.post("/api/recommendations/{rec_id}/approve")
def approve_recommendation(rec_id: int, db: Session = Depends(get_db)):
    """Human approves the agent's recommendation — executes the purchase order."""
    rec = (
        db.query(PurchasingRecommendation)
        .filter(PurchasingRecommendation.id == rec_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")

    if rec.status != RecommendationStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Recommendation is in '{rec.status.value}' state, not PENDING_APPROVAL",
        )

    # Get the latest agent decision
    decision = (
        db.query(AgentDecision)
        .filter(AgentDecision.recommendation_id == rec_id)
        .order_by(AgentDecision.created_at.desc())
        .first()
    )
    if not decision:
        raise HTTPException(status_code=400, detail="No agent decision found to approve")

    quantity = decision.suggested_quantity or rec.recommended_quantity
    supplier_id = rec.supplier_id or 1

    # Get unit price
    sp = (
        db.query(SupplierProduct)
        .filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == rec.product_id,
        )
        .first()
    )
    unit_price = sp.unit_price if sp else 10.0

    # Create the PO
    po = PurchaseOrder(
        product_id=rec.product_id,
        supplier_id=supplier_id,
        node_id=rec.node_id,
        quantity=quantity,
        unit_price=unit_price,
        total_price=quantity * unit_price,
        status=PurchaseOrderStatus.OPEN,
        created_at=datetime.now(timezone.utc),
    )
    db.add(po)
    db.flush()

    # Run deterministic validation on the created purchase order
    from app.validation.validator import validate_purchase_order
    validation = validate_purchase_order(db, po.id)
    
    db.add(AgentActivityLog(
        recommendation_id=rec_id,
        event_type="validation_passed" if validation.passed else "validation_failed",
        event_data={"checks": [c.model_dump() for c in validation.checks]},
        timestamp=datetime.now(timezone.utc),
    ))

    rec.status = RecommendationStatus.APPROVED

    db.add(AgentActivityLog(
        recommendation_id=rec_id,
        event_type="human_approved",
        event_data={"po_quantity": quantity, "approved_by": "buyer"},
        timestamp=datetime.now(timezone.utc),
    ))

    db.commit()

    return {
        "message": "Recommendation approved",
        "recommendation_id": rec_id,
        "purchase_order_id": po.id,
        "quantity": quantity,
        "total_price": po.total_price,
        "validation": validation.model_dump(),
    }


@router.post("/api/recommendations/{rec_id}/reject")
def reject_recommendation(rec_id: int, db: Session = Depends(get_db)):
    """Human rejects the agent's recommendation."""
    rec = (
        db.query(PurchasingRecommendation)
        .filter(PurchasingRecommendation.id == rec_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")

    rec.status = RecommendationStatus.REJECTED

    db.add(AgentActivityLog(
        recommendation_id=rec_id,
        event_type="human_rejected",
        event_data={"rejected_by": "buyer"},
        timestamp=datetime.now(timezone.utc),
    ))

    db.commit()
    return {"message": "Recommendation rejected", "recommendation_id": rec_id}
