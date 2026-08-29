"""
Deterministic Validation Engine for purchase orders.

This is the safety net that ensures business-critical constraints are NEVER
bypassed, regardless of what the LLM recommends. Each check is a pure function
that returns a ValidationCheck with pass/fail and a human-readable message.

Checks:
  1. Quantity must be positive
  2. Quantity must meet supplier MOQ
  3. Total cost must not exceed node budget
  4. Resulting inventory must not exceed storage capacity
  5. Supplier must have sufficient available quantity
  6. Purchase order must be structurally valid
"""

from sqlalchemy.orm import Session

from app.models.models import (
    PurchaseOrder, PurchaseOrderStatus, Supplier, Budget,
    FulfillmentNode, Inventory, SupplierProduct,
)
from app.schemas.schemas import ValidationCheck, ValidationResult


def validate_purchase_order(db: Session, order_id: int) -> ValidationResult:
    """Run all deterministic validation checks against a purchase order."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        return ValidationResult(
            passed=False,
            checks=[ValidationCheck(
                name="order_exists",
                passed=False,
                message=f"Purchase order {order_id} not found.",
            )],
            purchase_order_id=order_id,
        )

    checks = [
        _check_quantity_positive(order),
        _check_moq(db, order),
        _check_budget(db, order),
        _check_storage_capacity(db, order),
        _check_supplier_availability(db, order),
        _check_po_validity(order),
    ]

    return ValidationResult(
        passed=all(c.passed for c in checks),
        checks=checks,
        purchase_order_id=order_id,
    )


def validate_proposed_order(
    db: Session,
    product_id: int,
    supplier_id: int,
    node_id: int,
    quantity: int,
    unit_price: float,
) -> ValidationResult:
    """Validate a proposed (not yet created) purchase order.

    Used by the agent to pre-validate before creating a PO.
    """
    # Create a temporary object for validation (not persisted)
    proposed = PurchaseOrder(
        id=-1,
        product_id=product_id,
        supplier_id=supplier_id,
        node_id=node_id,
        quantity=quantity,
        unit_price=unit_price,
        total_price=quantity * unit_price,
        status=PurchaseOrderStatus.DRAFT,
    )

    checks = [
        _check_quantity_positive(proposed),
        _check_moq(db, proposed),
        _check_budget(db, proposed),
        _check_storage_capacity(db, proposed),
        _check_supplier_availability(db, proposed),
    ]

    return ValidationResult(
        passed=all(c.passed for c in checks),
        checks=checks,
    )


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_quantity_positive(order: PurchaseOrder) -> ValidationCheck:
    passed = order.quantity > 0
    return ValidationCheck(
        name="quantity",
        passed=passed,
        message=(
            f"Quantity {order.quantity} is valid."
            if passed
            else f"Quantity must be positive, got {order.quantity}."
        ),
        actual_value=float(order.quantity),
        limit_value=1.0,
    )


def _check_moq(db: Session, order: PurchaseOrder) -> ValidationCheck:
    supplier = db.query(Supplier).filter(Supplier.id == order.supplier_id).first()
    if not supplier:
        return ValidationCheck(
            name="moq",
            passed=False,
            message=f"Supplier {order.supplier_id} not found.",
        )

    passed = order.quantity >= supplier.minimum_order_quantity
    return ValidationCheck(
        name="moq",
        passed=passed,
        message=(
            f"Quantity {order.quantity} meets MOQ of {supplier.minimum_order_quantity}."
            if passed
            else f"Quantity {order.quantity} is below supplier MOQ of {supplier.minimum_order_quantity}."
        ),
        actual_value=float(order.quantity),
        limit_value=float(supplier.minimum_order_quantity),
    )


def _check_budget(db: Session, order: PurchaseOrder) -> ValidationCheck:
    budget = db.query(Budget).filter(Budget.node_id == order.node_id).first()
    if not budget:
        return ValidationCheck(
            name="budget",
            passed=False,
            message=f"No budget found for node {order.node_id}.",
        )

    total_cost = order.quantity * order.unit_price

    # Account for other open/approved orders at this node
    existing_committed = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.node_id == order.node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
            PurchaseOrder.id != order.id,  # Exclude the order being validated
        )
        .all()
    )
    committed_spend = sum(o.total_price for o in existing_committed)
    remaining_budget = budget.available_amount - committed_spend

    passed = total_cost <= remaining_budget
    return ValidationCheck(
        name="budget",
        passed=passed,
        message=(
            f"Order total ${total_cost:,.2f} is within remaining budget of ${remaining_budget:,.2f}."
            if passed
            else f"Order total ${total_cost:,.2f} exceeds remaining budget of ${remaining_budget:,.2f}."
        ),
        actual_value=total_cost,
        limit_value=remaining_budget,
    )


def _check_storage_capacity(db: Session, order: PurchaseOrder) -> ValidationCheck:
    node = db.query(FulfillmentNode).filter(FulfillmentNode.id == order.node_id).first()
    if not node:
        return ValidationCheck(
            name="storage",
            passed=False,
            message=f"Fulfillment node {order.node_id} not found.",
        )

    # Total current inventory at this node (all products)
    inventories = db.query(Inventory).filter(Inventory.node_id == order.node_id).all()
    current_total = sum(inv.current_quantity for inv in inventories)

    # Incoming from other open orders at this node
    open_orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.node_id == order.node_id,
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.OPEN,
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SUBMITTED,
            ]),
            PurchaseOrder.id != order.id,
        )
        .all()
    )
    incoming_total = sum(o.quantity for o in open_orders)

    projected_total = current_total + incoming_total + order.quantity
    remaining_capacity = node.storage_capacity - current_total - incoming_total

    passed = projected_total <= node.storage_capacity
    return ValidationCheck(
        name="storage",
        passed=passed,
        message=(
            f"Projected inventory {projected_total} units fits within capacity of {node.storage_capacity}."
            if passed
            else (
                f"Projected inventory {projected_total} units exceeds capacity of "
                f"{node.storage_capacity}. Remaining capacity: {remaining_capacity} units."
            )
        ),
        actual_value=float(projected_total),
        limit_value=float(node.storage_capacity),
    )


def _check_supplier_availability(db: Session, order: PurchaseOrder) -> ValidationCheck:
    supplier = db.query(Supplier).filter(Supplier.id == order.supplier_id).first()
    if not supplier:
        return ValidationCheck(
            name="supplier_availability",
            passed=False,
            message=f"Supplier {order.supplier_id} not found.",
        )

    passed = order.quantity <= supplier.available_quantity
    return ValidationCheck(
        name="supplier_availability",
        passed=passed,
        message=(
            f"Supplier '{supplier.name}' has {supplier.available_quantity} units available, "
            f"order requests {order.quantity}."
            if passed
            else (
                f"Supplier '{supplier.name}' only has {supplier.available_quantity} units available, "
                f"but order requests {order.quantity}."
            )
        ),
        actual_value=float(order.quantity),
        limit_value=float(supplier.available_quantity),
    )


def _check_po_validity(order: PurchaseOrder) -> ValidationCheck:
    """Check that the purchase order has valid structural data."""
    issues = []
    if not order.product_id:
        issues.append("Missing product_id")
    if not order.supplier_id:
        issues.append("Missing supplier_id")
    if not order.node_id:
        issues.append("Missing node_id")
    if order.unit_price <= 0:
        issues.append("unit_price must be positive")

    passed = len(issues) == 0
    return ValidationCheck(
        name="po_validity",
        passed=passed,
        message=(
            "Purchase order structure is valid."
            if passed
            else f"Purchase order has structural issues: {', '.join(issues)}."
        ),
    )
