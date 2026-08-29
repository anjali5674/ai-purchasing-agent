"""
Tests for the Demo Scenarios API and Dynamic Database Behavior.

Verifies:
1. Scenario list returns all 4 defined scenarios
2. Applying Scenario A updates Node 1 budget, storage, and inventory
3. Applying Scenario B restricts storage capacity to 400
4. Applying Scenario C restricts supplier available stock to 80
5. Applying Scenario D restricts budget to $500
6. Invalid scenario returns 404
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.database import Base, get_db
from app.models.models import (
    Product, FulfillmentNode, Inventory, DemandForecast,
    Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderStatus,
    Budget, PurchasingRecommendation, RecommendationStatus,
)

from sqlalchemy.pool import StaticPool

# Test DB setup with StaticPool for thread-safety in FastAPI TestClient
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    _seed_initial(db)
    yield
    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)


def _seed_initial(db):
    p = Product(id=1, sku="ALM-ORG-500", name="Organic Almonds 500g", category="Snacks", unit_price=12.5)
    n = FulfillmentNode(id=1, name="Downtown Hub", location="Centro", storage_capacity=2000)
    s1 = Supplier(id=1, name="NutriSource MX", lead_time_days=5, minimum_order_quantity=100, available_quantity=2000, reliability_score=0.95)
    s3 = Supplier(id=3, name="FreshDirect LATAM", lead_time_days=2, minimum_order_quantity=200, available_quantity=1500, reliability_score=0.88)
    sp = SupplierProduct(id=1, supplier_id=1, product_id=1, unit_price=11.0)
    b = Budget(id=1, node_id=1, available_amount=50000.0)
    inv = Inventory(id=1, product_id=1, node_id=1, current_quantity=120)
    df = DemandForecast(id=1, product_id=1, node_id=1, forecast_quantity=500, forecast_period="2026-Q4")
    po = PurchaseOrder(id=1, product_id=1, supplier_id=1, node_id=1, quantity=200, unit_price=11.0, total_price=2200.0, status=PurchaseOrderStatus.OPEN)
    rec = PurchasingRecommendation(id=1, product_id=1, node_id=1, supplier_id=1, recommended_quantity=800, status=RecommendationStatus.PENDING)

    db.add_all([p, n, s1, s3, sp, b, inv, df, po, rec])
    db.commit()


class TestDemoScenarios:
    def test_list_scenarios(self):
        res = client.get("/api/demo/scenarios")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 4
        scenario_ids = [s["id"] for s in data]
        assert "normal_replenishment" in scenario_ids
        assert "storage_constraint" in scenario_ids
        assert "supplier_constraint" in scenario_ids
        assert "budget_constraint" in scenario_ids

    def test_apply_normal_replenishment(self):
        res = client.post("/api/demo/scenarios/normal_replenishment")
        assert res.status_code == 200
        assert res.json()["scenario_id"] == "normal_replenishment"

        # Verify DB updated
        db = TestingSessionLocal()
        node = db.query(FulfillmentNode).filter(FulfillmentNode.id == 1).first()
        assert node.storage_capacity == 2000
        budget = db.query(Budget).filter(Budget.node_id == 1).first()
        assert budget.available_amount == 50000.00
        db.close()

    def test_apply_storage_constraint(self):
        res = client.post("/api/demo/scenarios/storage_constraint")
        assert res.status_code == 200
        assert res.json()["scenario_id"] == "storage_constraint"

        # Verify storage capacity reduced in DB
        db = TestingSessionLocal()
        node = db.query(FulfillmentNode).filter(FulfillmentNode.id == 1).first()
        assert node.storage_capacity == 400
        inv = db.query(Inventory).filter(Inventory.product_id == 1, Inventory.node_id == 1).first()
        assert inv.current_quantity == 250
        db.close()

    def test_apply_supplier_constraint(self):
        res = client.post("/api/demo/scenarios/supplier_constraint")
        assert res.status_code == 200

        # Verify supplier available stock reduced in DB
        db = TestingSessionLocal()
        s1 = db.query(Supplier).filter(Supplier.id == 1).first()
        assert s1.available_quantity == 80
        s3 = db.query(Supplier).filter(Supplier.id == 3).first()
        assert s3.available_quantity == 1500
        db.close()

    def test_apply_budget_constraint(self):
        res = client.post("/api/demo/scenarios/budget_constraint")
        assert res.status_code == 200

        # Verify budget reduced in DB
        db = TestingSessionLocal()
        budget = db.query(Budget).filter(Budget.node_id == 1).first()
        assert budget.available_amount == 500.00
        db.close()

    def test_apply_invalid_scenario_returns_404(self):
        res = client.post("/api/demo/scenarios/unknown_scenario")
        assert res.status_code == 404
