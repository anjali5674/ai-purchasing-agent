"""
Agent Tools — Functions the AI agent can call during investigation.

Each tool:
1. Queries the database for specific information
2. Logs an activity event for the recommendation
3. Returns structured data the LLM can reason about

The tools are registered as OpenAI function definitions so the LLM
can choose which tools to call and in what order.
"""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    Product, FulfillmentNode, Inventory, DemandForecast,
    Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderStatus,
    Budget, AgentActivityLog,
)


# ---------------------------------------------------------------------------
# Activity logging helper
# ---------------------------------------------------------------------------

def _log_activity(
    db: Session,
    recommendation_id: int,
    event_type: str,
    event_data: dict | None = None,
):
    """Record an agent activity event."""
    log = AgentActivityLog(
        recommendation_id=recommendation_id,
        event_type=event_type,
        event_data=event_data,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
    db.flush()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_product(db: Session, recommendation_id: int, product_id: int) -> dict:
    """Retrieve product details."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        result = {"error": f"Product {product_id} not found"}
    else:
        result = {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "unit_price": product.unit_price,
        }
    _log_activity(db, recommendation_id, "product_retrieved", result)
    return result


def get_inventory(db: Session, recommendation_id: int, product_id: int, node_id: int) -> dict:
    """Retrieve current inventory for a product at a fulfillment node."""
    inv = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id, Inventory.node_id == node_id)
        .first()
    )
    if not inv:
        result = {"product_id": product_id, "node_id": node_id, "current_quantity": 0}
    else:
        result = {
            "product_id": inv.product_id,
            "node_id": inv.node_id,
            "current_quantity": inv.current_quantity,
        }
    _log_activity(db, recommendation_id, "inventory_retrieved", result)
    return result


def get_demand_forecast(db: Session, recommendation_id: int, product_id: int, node_id: int) -> dict:
    """Retrieve demand forecast for a product at a node."""
    forecasts = (
        db.query(DemandForecast)
        .filter(
            DemandForecast.product_id == product_id,
            DemandForecast.node_id == node_id,
        )
        .all()
    )
    result = {
        "product_id": product_id,
        "node_id": node_id,
        "forecasts": [
            {
                "forecast_quantity": f.forecast_quantity,
                "forecast_period": f.forecast_period,
            }
            for f in forecasts
        ],
        "total_forecast": sum(f.forecast_quantity for f in forecasts),
    }
    _log_activity(db, recommendation_id, "forecast_retrieved", result)
    return result


def get_open_purchase_orders(db: Session, recommendation_id: int, product_id: int, node_id: int) -> dict:
    """Retrieve open/active purchase orders for a product at a node."""
    orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.product_id == product_id,
            PurchaseOrder.node_id == node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        )
        .all()
    )
    result = {
        "product_id": product_id,
        "node_id": node_id,
        "open_orders": [
            {
                "id": o.id,
                "quantity": o.quantity,
                "unit_price": o.unit_price,
                "total_price": o.total_price,
                "status": o.status.value,
                "supplier_id": o.supplier_id,
            }
            for o in orders
        ],
        "total_open_quantity": sum(o.quantity for o in orders),
    }
    _log_activity(db, recommendation_id, "open_pos_retrieved", result)
    return result


def get_supplier_details(db: Session, recommendation_id: int, supplier_id: int) -> dict:
    """Retrieve supplier information."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        result = {"error": f"Supplier {supplier_id} not found"}
    else:
        result = {
            "id": supplier.id,
            "name": supplier.name,
            "lead_time_days": supplier.lead_time_days,
            "minimum_order_quantity": supplier.minimum_order_quantity,
            "available_quantity": supplier.available_quantity,
            "reliability_score": supplier.reliability_score,
        }
    _log_activity(db, recommendation_id, "supplier_checked", result)
    return result


def get_alternative_suppliers(db: Session, recommendation_id: int, product_id: int) -> dict:
    """Find alternative suppliers for a product."""
    supplier_products = (
        db.query(SupplierProduct)
        .filter(SupplierProduct.product_id == product_id)
        .all()
    )
    alternatives = []
    for sp in supplier_products:
        supplier = db.query(Supplier).filter(Supplier.id == sp.supplier_id).first()
        if supplier:
            alternatives.append({
                "supplier_id": supplier.id,
                "name": supplier.name,
                "unit_price": sp.unit_price,
                "lead_time_days": supplier.lead_time_days,
                "minimum_order_quantity": supplier.minimum_order_quantity,
                "available_quantity": supplier.available_quantity,
                "reliability_score": supplier.reliability_score,
            })

    result = {
        "product_id": product_id,
        "alternative_suppliers": alternatives,
        "count": len(alternatives),
    }
    _log_activity(db, recommendation_id, "alternative_suppliers_checked", result)
    return result


def get_budget(db: Session, recommendation_id: int, node_id: int) -> dict:
    """Retrieve available budget for a fulfillment node."""
    budget = db.query(Budget).filter(Budget.node_id == node_id).first()

    # Calculate committed spend from open orders
    open_orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.node_id == node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        )
        .all()
    )
    committed_spend = sum(o.total_price for o in open_orders)

    if not budget:
        result = {"node_id": node_id, "error": "No budget found"}
    else:
        result = {
            "node_id": node_id,
            "total_budget": budget.available_amount,
            "committed_spend": committed_spend,
            "remaining_budget": budget.available_amount - committed_spend,
        }
    _log_activity(db, recommendation_id, "budget_checked", result)
    return result


def get_storage_capacity(db: Session, recommendation_id: int, node_id: int) -> dict:
    """Retrieve storage capacity and current utilization for a node."""
    node = db.query(FulfillmentNode).filter(FulfillmentNode.id == node_id).first()
    if not node:
        result = {"node_id": node_id, "error": "Node not found"}
        _log_activity(db, recommendation_id, "storage_checked", result)
        return result

    inventories = db.query(Inventory).filter(Inventory.node_id == node_id).all()
    current_total = sum(inv.current_quantity for inv in inventories)

    # Incoming from open orders
    open_orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.node_id == node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        )
        .all()
    )
    incoming = sum(o.quantity for o in open_orders)

    result = {
        "node_id": node_id,
        "node_name": node.name,
        "total_capacity": node.storage_capacity,
        "current_inventory": current_total,
        "incoming_from_open_orders": incoming,
        "projected_utilization": current_total + incoming,
        "remaining_capacity": node.storage_capacity - current_total - incoming,
    }
    _log_activity(db, recommendation_id, "storage_checked", result)
    return result


def calculate_purchase_quantity(
    db: Session,
    recommendation_id: int,
    product_id: int,
    node_id: int,
) -> dict:
    """Calculate a suggested purchase quantity based on demand, inventory, and open POs."""
    inv = get_inventory.__wrapped__(db, product_id, node_id) if hasattr(get_inventory, '__wrapped__') else \
        _raw_inventory(db, product_id, node_id)

    forecasts = (
        db.query(DemandForecast)
        .filter(DemandForecast.product_id == product_id, DemandForecast.node_id == node_id)
        .all()
    )
    total_demand = sum(f.forecast_quantity for f in forecasts)

    open_orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.product_id == product_id,
            PurchaseOrder.node_id == node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
        )
        .all()
    )
    total_open = sum(o.quantity for o in open_orders)

    current_qty = inv
    net_need = max(0, total_demand - current_qty - total_open)

    result = {
        "product_id": product_id,
        "node_id": node_id,
        "current_inventory": current_qty,
        "total_forecast_demand": total_demand,
        "total_open_order_quantity": total_open,
        "net_need": net_need,
        "suggested_quantity": net_need,
    }
    _log_activity(db, recommendation_id, "quantity_calculated", result)
    return result


def _raw_inventory(db: Session, product_id: int, node_id: int) -> int:
    inv = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id, Inventory.node_id == node_id)
        .first()
    )
    return inv.current_quantity if inv else 0


# ---------------------------------------------------------------------------
# OpenAI Tool Definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Retrieve product details including SKU, name, category, and unit price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID to look up."},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Get current inventory quantity for a product at a specific fulfillment node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID."},
                    "node_id": {"type": "integer", "description": "The fulfillment node ID."},
                },
                "required": ["product_id", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_demand_forecast",
            "description": "Get demand forecast for a product at a specific fulfillment node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID."},
                    "node_id": {"type": "integer", "description": "The fulfillment node ID."},
                },
                "required": ["product_id", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_open_purchase_orders",
            "description": "Get all open/active purchase orders for a product at a node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID."},
                    "node_id": {"type": "integer", "description": "The fulfillment node ID."},
                },
                "required": ["product_id", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_supplier_details",
            "description": "Get supplier details including lead time, MOQ, available quantity, and reliability score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "supplier_id": {"type": "integer", "description": "The supplier ID."},
                },
                "required": ["supplier_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alternative_suppliers",
            "description": "Find alternative suppliers that can provide a specific product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID."},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget",
            "description": "Get available budget for a fulfillment node, including committed spend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "integer", "description": "The fulfillment node ID."},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_storage_capacity",
            "description": "Get storage capacity and current utilization for a fulfillment node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "integer", "description": "The fulfillment node ID."},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_purchase_quantity",
            "description": "Calculate suggested purchase quantity based on demand minus inventory minus open POs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product ID."},
                    "node_id": {"type": "integer", "description": "The fulfillment node ID."},
                },
                "required": ["product_id", "node_id"],
            },
        },
    },
]


def get_gemini_tools():
    """Build Gemini SDK Tool specifications from function definitions."""
    from google.genai import types

    declarations = [
        types.FunctionDeclaration(
            name="get_product",
            description="Retrieve product details including SKU, name, category, and unit price.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.INTEGER, description="The product ID to look up."),
                },
                required=["product_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_inventory",
            description="Get current inventory quantity for a product at a specific fulfillment node.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.INTEGER, description="The product ID."),
                    "node_id": types.Schema(type=types.Type.INTEGER, description="The fulfillment node ID."),
                },
                required=["product_id", "node_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_demand_forecast",
            description="Get demand forecast for a product at a specific fulfillment node.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.INTEGER, description="The product ID."),
                    "node_id": types.Schema(type=types.Type.INTEGER, description="The fulfillment node ID."),
                },
                required=["product_id", "node_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_open_purchase_orders",
            description="Get all open/active purchase orders for a product at a node.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.INTEGER, description="The product ID."),
                    "node_id": types.Schema(type=types.Type.INTEGER, description="The fulfillment node ID."),
                },
                required=["product_id", "node_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_supplier_details",
            description="Get supplier details including lead time, MOQ, available quantity, and reliability score.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "supplier_id": types.Schema(type=types.Type.INTEGER, description="The supplier ID."),
                },
                required=["supplier_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_alternative_suppliers",
            description="Find alternative suppliers that can provide a specific product.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.INTEGER, description="The product ID."),
                },
                required=["product_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_budget",
            description="Get available budget for a fulfillment node, including committed spend.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "node_id": types.Schema(type=types.Type.INTEGER, description="The fulfillment node ID."),
                },
                required=["node_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_storage_capacity",
            description="Get storage capacity and current utilization for a fulfillment node.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "node_id": types.Schema(type=types.Type.INTEGER, description="The fulfillment node ID."),
                },
                required=["node_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="calculate_purchase_quantity",
            description="Calculate suggested purchase quantity based on demand minus inventory minus open POs.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(type=types.Type.INTEGER, description="The product ID."),
                    "node_id": types.Schema(type=types.Type.INTEGER, description="The fulfillment node ID."),
                },
                required=["product_id", "node_id"],
            ),
        ),
    ]

    return [types.Tool(function_declarations=declarations)]


# ---------------------------------------------------------------------------
# Tool dispatcher — maps tool name to function call
# ---------------------------------------------------------------------------

def execute_tool(
    db: Session,
    recommendation_id: int,
    tool_name: str,
    arguments: dict,
) -> Any:
    """Execute an agent tool by name with the given arguments."""
    tool_map = {
        "get_product": lambda args: get_product(db, recommendation_id, **args),
        "get_inventory": lambda args: get_inventory(db, recommendation_id, **args),
        "get_demand_forecast": lambda args: get_demand_forecast(db, recommendation_id, **args),
        "get_open_purchase_orders": lambda args: get_open_purchase_orders(db, recommendation_id, **args),
        "get_supplier_details": lambda args: get_supplier_details(db, recommendation_id, **args),
        "get_alternative_suppliers": lambda args: get_alternative_suppliers(db, recommendation_id, **args),
        "get_budget": lambda args: get_budget(db, recommendation_id, **args),
        "get_storage_capacity": lambda args: get_storage_capacity(db, recommendation_id, **args),
        "calculate_purchase_quantity": lambda args: calculate_purchase_quantity(db, recommendation_id, **args),
    }

    if tool_name not in tool_map:
        return {"error": f"Unknown tool: {tool_name}"}

    return tool_map[tool_name](arguments)

