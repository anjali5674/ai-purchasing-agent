"""Dashboard API — Summary stats for the frontend dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import (
    PurchasingRecommendation, RecommendationStatus,
    PurchaseOrder, PurchaseOrderStatus,
    AgentDecision,
)
from app.schemas.schemas import DashboardSummary, AgentDecisionResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    pending_recs = (
        db.query(PurchasingRecommendation)
        .filter(PurchasingRecommendation.status == RecommendationStatus.PENDING)
        .count()
    )
    pending_approvals = (
        db.query(PurchasingRecommendation)
        .filter(PurchasingRecommendation.status == RecommendationStatus.PENDING_APPROVAL)
        .count()
    )

    # Count POs with failed validation (CANCELLED status as a proxy)
    validation_failures = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.status == PurchaseOrderStatus.CANCELLED)
        .count()
    )

    active_pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.status.in_([
            PurchaseOrderStatus.OPEN,
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.SUBMITTED,
        ]))
        .count()
    )

    recent_decisions = (
        db.query(AgentDecision)
        .order_by(AgentDecision.created_at.desc())
        .limit(10)
        .all()
    )

    return DashboardSummary(
        pending_recommendations=pending_recs,
        pending_approvals=pending_approvals,
        validation_failures=validation_failures,
        active_purchase_orders=active_pos,
        recent_decisions=[AgentDecisionResponse.model_validate(d) for d in recent_decisions],
    )
