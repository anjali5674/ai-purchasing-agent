"""Inventory API — Read-only endpoints for inventory data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database.database import get_db
from app.models.models import Inventory
from app.schemas.schemas import InventoryResponse

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("", response_model=list[InventoryResponse])
def list_inventory(
    product_id: int | None = Query(None),
    node_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Inventory).options(
        joinedload(Inventory.product),
        joinedload(Inventory.node),
    )
    if product_id:
        query = query.filter(Inventory.product_id == product_id)
    if node_id:
        query = query.filter(Inventory.node_id == node_id)
    return query.all()
