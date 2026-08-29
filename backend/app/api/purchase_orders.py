"""Purchase Orders API — CRUD + validation endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models.models import PurchaseOrder, PurchaseOrderStatus
from app.schemas.schemas import (
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
    ValidationResult,
)
from app.validation.validator import validate_purchase_order

router = APIRouter(prefix="/api/purchase-orders", tags=["Purchase Orders"])


@router.get("", response_model=list[PurchaseOrderResponse])
def list_purchase_orders(db: Session = Depends(get_db)):
    return (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.product),
            joinedload(PurchaseOrder.supplier),
            joinedload(PurchaseOrder.node),
        )
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.product),
            joinedload(PurchaseOrder.supplier),
            joinedload(PurchaseOrder.node),
        )
        .filter(PurchaseOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"Purchase order {order_id} not found")
    return order


@router.post("", response_model=PurchaseOrderResponse, status_code=201)
def create_purchase_order(body: PurchaseOrderCreate, db: Session = Depends(get_db)):
    order = PurchaseOrder(
        product_id=body.product_id,
        supplier_id=body.supplier_id,
        node_id=body.node_id,
        quantity=body.quantity,
        unit_price=body.unit_price,
        total_price=body.quantity * body.unit_price,
        status=PurchaseOrderStatus.DRAFT,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=PurchaseOrderResponse)
def update_purchase_order(order_id: int, body: PurchaseOrderUpdate, db: Session = Depends(get_db)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Purchase order {order_id} not found")

    if body.quantity is not None:
        order.quantity = body.quantity
        order.total_price = body.quantity * (body.unit_price or order.unit_price)
    if body.unit_price is not None:
        order.unit_price = body.unit_price
        order.total_price = order.quantity * body.unit_price
    if body.status is not None:
        try:
            order.status = PurchaseOrderStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/validate", response_model=ValidationResult)
def validate_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Purchase order {order_id} not found")
    return validate_purchase_order(db, order_id)
