"""
Seed data for the AI Purchasing Agent demo.

Creates realistic purchasing scenarios designed to produce different agent outcomes:
  #1 Organic Almonds  → MODIFY  (storage exceeded, open POs cover partial demand)
  #2 Cold Brew Coffee → ACCEPT  (all constraints pass)
  #3 Protein Bars     → REJECT  (budget insufficient)
  #4 Fresh OJ         → ACCEPT  (straightforward replenishment)
  #5 Coconut Water    → INVESTIGATE (low supplier reliability, uncertain demand)
"""

from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.database.database import engine, Base, SessionLocal
from app.models.models import (
    Product, FulfillmentNode, Inventory, DemandForecast,
    Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderStatus,
    Budget, PurchasingRecommendation, RecommendationStatus,
)


def seed_database():
    """Drop all tables, recreate, and insert seed data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_products(db)
        _seed_nodes(db)
        _seed_suppliers(db)
        _seed_supplier_products(db)
        _seed_inventory(db)
        _seed_forecasts(db)
        _seed_budgets(db)
        _seed_purchase_orders(db)
        _seed_recommendations(db)
        db.commit()
        print("[OK] Database seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()


def _seed_products(db: Session):
    products = [
        Product(id=1, sku="ALM-ORG-500", name="Organic Almonds 500g", category="Snacks & Nuts", unit_price=12.50),
        Product(id=2, sku="CBR-RTD-330", name="Cold Brew Coffee 330ml", category="Beverages", unit_price=4.20),
        Product(id=3, sku="PRO-BAR-60G", name="Protein Bar 60g", category="Health & Fitness", unit_price=3.80),
        Product(id=4, sku="OJ-FRESH-1L", name="Fresh Orange Juice 1L", category="Beverages", unit_price=5.50),
        Product(id=5, sku="COC-WAT-500", name="Coconut Water 500ml", category="Beverages", unit_price=3.00),
    ]
    db.add_all(products)
    db.flush()


def _seed_nodes(db: Session):
    nodes = [
        FulfillmentNode(id=1, name="Downtown Hub", location="Mexico City - Centro", storage_capacity=2000),
        FulfillmentNode(id=2, name="North Distribution Center", location="Mexico City - Polanco", storage_capacity=5000),
        FulfillmentNode(id=3, name="South Micro-Fulfillment", location="Mexico City - Coyoacán", storage_capacity=800),
    ]
    db.add_all(nodes)
    db.flush()


def _seed_suppliers(db: Session): 
    suppliers = [
        Supplier(
            id=1, name="NutriSource MX",
            lead_time_days=5, minimum_order_quantity=100,
            available_quantity=2000, reliability_score=0.95,
        ),
        Supplier(
            id=2, name="BevCo Distribuidora",
            lead_time_days=3, minimum_order_quantity=50,
            available_quantity=5000, reliability_score=0.92,
        ),
        Supplier(
            id=3, name="FreshDirect LATAM",
            lead_time_days=2, minimum_order_quantity=200,
            available_quantity=1500, reliability_score=0.88,
        ),
        Supplier(
            id=4, name="Tropical Imports Co",
            lead_time_days=14, minimum_order_quantity=300,
            available_quantity=800, reliability_score=0.50,
        ),
        Supplier(
            id=5, name="Global Fresh Foods",
            lead_time_days=7, minimum_order_quantity=100,
            available_quantity=1200, reliability_score=0.92,
        ),
        Supplier(
            id=6, name="Sunrise Wholesale Ltd",
            lead_time_days=10, minimum_order_quantity=200,
            available_quantity=950, reliability_score=0.85,
        ),
    ]
    db.add_all(suppliers)
    db.flush()


def _seed_supplier_products(db: Session):
    """Map suppliers to products they can provide."""
    mappings = [
        # Product 1 (Almonds) — supplied by NutriSource and FreshDirect
        SupplierProduct(supplier_id=1, product_id=1, unit_price=11.00),
        SupplierProduct(supplier_id=3, product_id=1, unit_price=12.00),
        SupplierProduct(supplier_id=4, product_id=1, unit_price=17.00),
        # Product 2 (Cold Brew) — supplied by BevCo and Global Fresh
        SupplierProduct(supplier_id=2, product_id=2, unit_price=3.50),
        SupplierProduct(supplier_id=5, product_id=2, unit_price=3.80),
        # Product 3 (Protein Bars) — supplied by NutriSource and Sunrise Wholesale
        SupplierProduct(supplier_id=1, product_id=3, unit_price=3.20),
        SupplierProduct(supplier_id=6, product_id=3, unit_price=3.00),
        # Product 4 (OJ) — supplied by FreshDirect and BevCo
        SupplierProduct(supplier_id=3, product_id=4, unit_price=4.80),
        SupplierProduct(supplier_id=2, product_id=4, unit_price=5.00),
        # Product 5 (Coconut Water) — supplied by Tropical Imports and BevCo
        SupplierProduct(supplier_id=4, product_id=5, unit_price=2.50),
        SupplierProduct(supplier_id=2, product_id=5, unit_price=2.80),
    ]
    db.add_all(mappings)
    db.flush()


def _seed_inventory(db: Session):
    """Current stock at each node."""
    inventories = [
        # Node 1 — Downtown Hub
        Inventory(product_id=1, node_id=1, current_quantity=120),
        Inventory(product_id=2, node_id=1, current_quantity=80),
        Inventory(product_id=3, node_id=1, current_quantity=200),
        Inventory(product_id=4, node_id=1, current_quantity=50),
        Inventory(product_id=5, node_id=1, current_quantity=30),
        # Node 2 — North DC
        Inventory(product_id=1, node_id=2, current_quantity=500),
        Inventory(product_id=2, node_id=2, current_quantity=300),
        Inventory(product_id=3, node_id=2, current_quantity=800),
        Inventory(product_id=4, node_id=2, current_quantity=150),
        Inventory(product_id=5, node_id=2, current_quantity=100),
        # Node 3 — South Micro
        Inventory(product_id=1, node_id=3, current_quantity=40),
        Inventory(product_id=2, node_id=3, current_quantity=20),
        Inventory(product_id=3, node_id=3, current_quantity=60),
        Inventory(product_id=4, node_id=3, current_quantity=15),
        Inventory(product_id=5, node_id=3, current_quantity=10),
    ]
    db.add_all(inventories)
    db.flush()


def _seed_forecasts(db: Session):
    """Q4 2026 demand forecasts per product per node."""
    forecasts = [
        # Node 1
        DemandForecast(product_id=1, node_id=1, forecast_quantity=600, forecast_period="2026-Q4"),
        DemandForecast(product_id=2, node_id=1, forecast_quantity=250, forecast_period="2026-Q4"),
        DemandForecast(product_id=3, node_id=1, forecast_quantity=400, forecast_period="2026-Q4"),
        DemandForecast(product_id=4, node_id=1, forecast_quantity=350, forecast_period="2026-Q4"),
        DemandForecast(product_id=5, node_id=1, forecast_quantity=200, forecast_period="2026-Q4"),
        # Node 2
        DemandForecast(product_id=1, node_id=2, forecast_quantity=1200, forecast_period="2026-Q4"),
        DemandForecast(product_id=2, node_id=2, forecast_quantity=800, forecast_period="2026-Q4"),
        DemandForecast(product_id=3, node_id=2, forecast_quantity=1500, forecast_period="2026-Q4"),
        DemandForecast(product_id=4, node_id=2, forecast_quantity=500, forecast_period="2026-Q4"),
        DemandForecast(product_id=5, node_id=2, forecast_quantity=400, forecast_period="2026-Q4"),
        # Node 3
        DemandForecast(product_id=1, node_id=3, forecast_quantity=150, forecast_period="2026-Q4"),
        DemandForecast(product_id=2, node_id=3, forecast_quantity=100, forecast_period="2026-Q4"),
        DemandForecast(product_id=3, node_id=3, forecast_quantity=200, forecast_period="2026-Q4"),
        DemandForecast(product_id=4, node_id=3, forecast_quantity=80, forecast_period="2026-Q4"),
        DemandForecast(product_id=5, node_id=3, forecast_quantity=50, forecast_period="2026-Q4"),
    ]
    db.add_all(forecasts)
    db.flush()


def _seed_budgets(db: Session):
    """Monthly purchasing budgets per node."""
    budgets = [
        Budget(node_id=1, available_amount=50000.00),
        Budget(node_id=2, available_amount=120000.00),
        Budget(node_id=3, available_amount=8000.00),
    ]
    db.add_all(budgets)
    db.flush()


def _seed_purchase_orders(db: Session):
    """Existing in-flight purchase orders."""
    orders = [
        # Almonds inbound to Node 1 — 300 units from NutriSource MX
        PurchaseOrder(
            product_id=1, supplier_id=1, node_id=1,
            quantity=300, unit_price=11.00, total_price=3300.00,
            status=PurchaseOrderStatus.OPEN,
            created_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ),
        # OJ inbound to Node 1 — 50 units from FreshDirect LATAM
        PurchaseOrder(
            product_id=4, supplier_id=3, node_id=1,
            quantity=50, unit_price=4.80, total_price=240.00,
            status=PurchaseOrderStatus.OPEN,
            created_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
        ),
    ]
    db.add_all(orders)
    db.flush()


def _seed_recommendations(db: Session):
    """
    5 purchasing recommendations, each designed to produce a different outcome.
    """
    recommendations = [
        # #1 — MODIFY: 800 almonds, but storage is limited + open PO exists
        PurchasingRecommendation(
            id=1, product_id=1, node_id=1,
            supplier_id=1, secondary_supplier_id=3,
            recommended_quantity=800,
            status=RecommendationStatus.PENDING,
        ),
        # #2 — ACCEPT: 200 cold brew, all constraints pass
        PurchasingRecommendation(
            id=2, product_id=2, node_id=1,
            supplier_id=2, secondary_supplier_id=5,
            recommended_quantity=200,
            status=RecommendationStatus.PENDING,
        ),
        # #3 — REJECT: 1500 protein bars, budget at Node 3 is only $8000
        PurchasingRecommendation(
            id=3, product_id=3, node_id=3,
            supplier_id=1, secondary_supplier_id=6,
            recommended_quantity=1500,
            status=RecommendationStatus.PENDING,
        ),
        # #4 — ACCEPT: 300 OJ, straightforward replenishment at Node 1
        PurchasingRecommendation(
            id=4, product_id=4, node_id=1,
            supplier_id=3, secondary_supplier_id=2,
            recommended_quantity=300,
            status=RecommendationStatus.PENDING,
        ),
        # #5 — INVESTIGATE: 600 coconut water, supplier reliability 0.50
        PurchasingRecommendation(
            id=5, product_id=5, node_id=1,
            supplier_id=4, secondary_supplier_id=2,
            recommended_quantity=600,
            status=RecommendationStatus.PENDING,
        ),
    ]
    db.add_all(recommendations)
    db.flush()


if __name__ == "__main__":
    seed_database()
