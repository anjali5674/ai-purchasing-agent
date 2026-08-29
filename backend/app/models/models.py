"""
SQLAlchemy ORM models for the AI Purchasing Agent.

All 10 models represent the purchasing domain:
- Product, FulfillmentNode, Inventory, DemandForecast (master data)
- Supplier, SupplierProduct (supplier data)
- PurchaseOrder, Budget (transactional data)
- PurchasingRecommendation, AgentDecision, AgentActivityLog (agent data)
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship

from app.database.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class RecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    INVESTIGATING = "INVESTIGATING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"


class AgentDecisionType(str, enum.Enum):
    ACCEPT = "ACCEPT"
    MODIFY = "MODIFY"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Master Data
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    unit_price = Column(Float, nullable=False)

    inventories = relationship("Inventory", back_populates="product")
    forecasts = relationship("DemandForecast", back_populates="product")
    purchase_orders = relationship("PurchaseOrder", back_populates="product")
    recommendations = relationship("PurchasingRecommendation", back_populates="product")
    supplier_products = relationship("SupplierProduct", back_populates="product")


class FulfillmentNode(Base):
    __tablename__ = "fulfillment_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=False)
    storage_capacity = Column(Integer, nullable=False)

    inventories = relationship("Inventory", back_populates="node")
    forecasts = relationship("DemandForecast", back_populates="node")
    purchase_orders = relationship("PurchaseOrder", back_populates="node")
    recommendations = relationship("PurchasingRecommendation", back_populates="node")
    budgets = relationship("Budget", back_populates="node")


class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("fulfillment_nodes.id"), nullable=False)
    current_quantity = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="inventories")
    node = relationship("FulfillmentNode", back_populates="inventories")


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("fulfillment_nodes.id"), nullable=False)
    forecast_quantity = Column(Integer, nullable=False)
    forecast_period = Column(String(50), nullable=False)  # e.g. "2026-Q3", "2026-09"

    product = relationship("Product", back_populates="forecasts")
    node = relationship("FulfillmentNode", back_populates="forecasts")


# ---------------------------------------------------------------------------
# Supplier Data
# ---------------------------------------------------------------------------

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    minimum_order_quantity = Column(Integer, nullable=False)
    available_quantity = Column(Integer, nullable=False)
    reliability_score = Column(Float, nullable=False)  # 0.0 to 1.0

    supplier_products = relationship("SupplierProduct", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class SupplierProduct(Base):
    """Join table: which suppliers can provide which products."""
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    unit_price = Column(Float, nullable=False)  # Supplier-specific pricing

    supplier = relationship("Supplier", back_populates="supplier_products")
    product = relationship("Product", back_populates="supplier_products")


# ---------------------------------------------------------------------------
# Transactional Data
# ---------------------------------------------------------------------------

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("fulfillment_nodes.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(Enum(PurchaseOrderStatus), nullable=False, default=PurchaseOrderStatus.DRAFT)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    node = relationship("FulfillmentNode", back_populates="purchase_orders")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("fulfillment_nodes.id"), nullable=False)
    available_amount = Column(Float, nullable=False)

    node = relationship("FulfillmentNode", back_populates="budgets")


# ---------------------------------------------------------------------------
# Agent Data
# ---------------------------------------------------------------------------

class PurchasingRecommendation(Base):
    __tablename__ = "purchasing_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("fulfillment_nodes.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    recommended_quantity = Column(Integer, nullable=False)
    status = Column(
        Enum(RecommendationStatus),
        nullable=False,
        default=RecommendationStatus.PENDING,
    )
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="recommendations")
    node = relationship("FulfillmentNode", back_populates="recommendations")
    decisions = relationship("AgentDecision", back_populates="recommendation")
    activity_logs = relationship(
        "AgentActivityLog",
        back_populates="recommendation",
        order_by="AgentActivityLog.timestamp",
    )


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(
        Integer, ForeignKey("purchasing_recommendations.id"), nullable=False
    )
    decision = Column(Enum(AgentDecisionType), nullable=False)
    suggested_quantity = Column(Integer, nullable=True)
    reasoning = Column(Text, nullable=False)
    important_factors = Column(JSON, nullable=True)  # list of strings
    constraints_checked = Column(JSON, nullable=True)  # list of strings
    confidence = Column(Enum(ConfidenceLevel), nullable=False)
    requires_human_approval = Column(Integer, nullable=False, default=0)  # 0/1 boolean
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    recommendation = relationship("PurchasingRecommendation", back_populates="decisions")


class AgentActivityLog(Base):
    __tablename__ = "agent_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(
        Integer, ForeignKey("purchasing_recommendations.id"), nullable=False
    )
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    recommendation = relationship("PurchasingRecommendation", back_populates="activity_logs")
