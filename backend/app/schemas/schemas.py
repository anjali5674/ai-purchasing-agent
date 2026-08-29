"""
Pydantic schemas for API request/response serialization.

Organized by domain: Products, Inventory, Forecasts, Suppliers,
PurchaseOrders, Recommendations, Agent, Validation, Dashboard.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    unit_price: float

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Fulfillment Node
# ---------------------------------------------------------------------------

class FulfillmentNodeResponse(BaseModel):
    id: int
    name: str
    location: str
    storage_capacity: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    node_id: int
    current_quantity: int
    product: Optional[ProductResponse] = None
    node: Optional[FulfillmentNodeResponse] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Demand Forecast
# ---------------------------------------------------------------------------

class DemandForecastResponse(BaseModel):
    id: int
    product_id: int
    node_id: int
    forecast_quantity: int
    forecast_period: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------

class SupplierResponse(BaseModel):
    id: int
    name: str
    lead_time_days: int
    minimum_order_quantity: int
    available_quantity: int
    reliability_score: float

    model_config = {"from_attributes": True}


class SupplierProductResponse(BaseModel):
    id: int
    supplier_id: int
    product_id: int
    unit_price: float
    supplier: Optional[SupplierResponse] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------

class PurchaseOrderCreate(BaseModel):
    product_id: int
    supplier_id: int
    node_id: int
    quantity: int
    unit_price: float


class PurchaseOrderUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    status: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    id: int
    product_id: int
    supplier_id: int
    node_id: int
    quantity: int
    unit_price: float
    total_price: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    product: Optional[ProductResponse] = None
    supplier: Optional[SupplierResponse] = None
    node: Optional[FulfillmentNodeResponse] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class BudgetResponse(BaseModel):
    id: int
    node_id: int
    available_amount: float

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agent Decision
# ---------------------------------------------------------------------------

class AgentDecisionResponse(BaseModel):
    id: int
    recommendation_id: int
    decision: str
    suggested_quantity: Optional[int] = None
    reasoning: str
    important_factors: Optional[list] = None
    constraints_checked: Optional[list] = None
    confidence: str
    requires_human_approval: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agent Activity Log
# ---------------------------------------------------------------------------

class AgentActivityLogResponse(BaseModel):
    id: int
    recommendation_id: int
    event_type: str
    event_data: Optional[dict] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Purchasing Recommendation
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    id: int
    product_id: int
    node_id: int
    supplier_id: Optional[int] = None
    recommended_quantity: int
    status: str
    created_at: datetime
    product: Optional[ProductResponse] = None
    node: Optional[FulfillmentNodeResponse] = None
    decisions: Optional[list[AgentDecisionResponse]] = None
    activity_logs: Optional[list[AgentActivityLogResponse]] = None

    model_config = {"from_attributes": True}


class RecommendationListResponse(BaseModel):
    """Lightweight version for list views (no nested decisions/logs)."""
    id: int
    product_id: int
    node_id: int
    supplier_id: Optional[int] = None
    recommended_quantity: int
    status: str
    created_at: datetime
    product: Optional[ProductResponse] = None
    node: Optional[FulfillmentNodeResponse] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str
    actual_value: Optional[float] = None
    limit_value: Optional[float] = None


class ValidationResult(BaseModel):
    passed: bool
    checks: list[ValidationCheck]
    purchase_order_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Agent Review Request / Response
# ---------------------------------------------------------------------------

class AgentReviewRequest(BaseModel):
    """Optional parameters when triggering an agent review."""
    context: Optional[str] = None  # Additional context for the agent


class AgentReviewResponse(BaseModel):
    recommendation_id: int
    decision: AgentDecisionResponse
    validation: Optional[ValidationResult] = None
    purchase_order: Optional[PurchaseOrderResponse] = None
    feedback_iterations: int = 0


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    pending_recommendations: int
    pending_approvals: int
    validation_failures: int
    active_purchase_orders: int
    recent_decisions: list[AgentDecisionResponse]
