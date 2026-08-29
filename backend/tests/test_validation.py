"""
Tests for the deterministic Validation Engine.

These tests verify that business-critical constraints are enforced
regardless of what the LLM recommends. No OpenAI API calls are made.

Tests:
1. Budget pass/fail
2. MOQ pass/fail
3. Storage capacity pass/fail
4. Supplier availability pass/fail
5. Quantity positive check
6. Full validation pass/fail
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.models import (
    Product, FulfillmentNode, Inventory, Supplier, SupplierProduct,
    PurchaseOrder, PurchaseOrderStatus, Budget,
)
from app.validation.validator import validate_purchase_order, validate_proposed_order


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed test data
    _seed_test_data(session)

    yield session

    session.close()


def _seed_test_data(db):
    """Insert minimal test data."""
    # Product
    db.add(Product(id=1, sku="TEST-001", name="Test Product", category="Test", unit_price=10.0))

    # Node with 1000 capacity
    db.add(FulfillmentNode(id=1, name="Test Node", location="Test City", storage_capacity=1000))

    # Inventory: 200 units at node 1
    db.add(Inventory(product_id=1, node_id=1, current_quantity=200))

    # Supplier with MOQ=100, available=2000
    db.add(Supplier(
        id=1, name="Test Supplier",
        lead_time_days=5, minimum_order_quantity=100,
        available_quantity=2000, reliability_score=0.95,
    ))

    # Supplier-Product link
    db.add(SupplierProduct(supplier_id=1, product_id=1, unit_price=10.0))

    # Budget: $50,000
    db.add(Budget(node_id=1, available_amount=50000.0))

    db.commit()


def _create_test_po(db, quantity=500, unit_price=10.0, status=PurchaseOrderStatus.DRAFT) -> PurchaseOrder:
    """Helper to create a test purchase order."""
    po = PurchaseOrder(
        product_id=1, supplier_id=1, node_id=1,
        quantity=quantity, unit_price=unit_price,
        total_price=quantity * unit_price,
        status=status,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


# ---------------------------------------------------------------------------
# Budget tests
# ---------------------------------------------------------------------------

class TestBudgetValidation:
    def test_budget_pass(self, db):
        """Order total within budget should pass."""
        po = _create_test_po(db, quantity=500, unit_price=10.0)  # $5,000 < $50,000
        result = validate_purchase_order(db, po.id)
        budget_check = next(c for c in result.checks if c.name == "budget")
        assert budget_check.passed is True

    def test_budget_fail(self, db):
        """Order total exceeding budget should fail."""
        po = _create_test_po(db, quantity=6000, unit_price=10.0)  # $60,000 > $50,000
        result = validate_purchase_order(db, po.id)
        budget_check = next(c for c in result.checks if c.name == "budget")
        assert budget_check.passed is False
        assert "exceeds" in budget_check.message.lower()

    def test_budget_accounts_for_existing_orders(self, db):
        """Budget check should account for already committed open orders."""
        # Create an existing open order for $45,000
        _create_test_po(db, quantity=4500, unit_price=10.0, status=PurchaseOrderStatus.OPEN)
        # Now try to create another for $6,000 — should fail (45k + 6k > 50k)
        po = _create_test_po(db, quantity=600, unit_price=10.0)
        result = validate_purchase_order(db, po.id)
        budget_check = next(c for c in result.checks if c.name == "budget")
        assert budget_check.passed is False


# ---------------------------------------------------------------------------
# MOQ tests
# ---------------------------------------------------------------------------

class TestMOQValidation:
    def test_moq_pass(self, db):
        """Quantity meeting MOQ should pass."""
        po = _create_test_po(db, quantity=100)  # MOQ=100
        result = validate_purchase_order(db, po.id)
        moq_check = next(c for c in result.checks if c.name == "moq")
        assert moq_check.passed is True

    def test_moq_pass_above(self, db):
        """Quantity above MOQ should pass."""
        po = _create_test_po(db, quantity=500)
        result = validate_purchase_order(db, po.id)
        moq_check = next(c for c in result.checks if c.name == "moq")
        assert moq_check.passed is True

    def test_moq_fail(self, db):
        """Quantity below MOQ should fail."""
        po = _create_test_po(db, quantity=50)  # 50 < MOQ=100
        result = validate_purchase_order(db, po.id)
        moq_check = next(c for c in result.checks if c.name == "moq")
        assert moq_check.passed is False
        assert "below" in moq_check.message.lower()


# ---------------------------------------------------------------------------
# Storage capacity tests
# ---------------------------------------------------------------------------

class TestStorageValidation:
    def test_storage_pass(self, db):
        """Order fitting within remaining storage should pass."""
        po = _create_test_po(db, quantity=500)  # 200 existing + 500 = 700 < 1000
        result = validate_purchase_order(db, po.id)
        storage_check = next(c for c in result.checks if c.name == "storage")
        assert storage_check.passed is True

    def test_storage_fail(self, db):
        """Order exceeding storage capacity should fail."""
        po = _create_test_po(db, quantity=900)  # 200 existing + 900 = 1100 > 1000
        result = validate_purchase_order(db, po.id)
        storage_check = next(c for c in result.checks if c.name == "storage")
        assert storage_check.passed is False
        assert "exceeds" in storage_check.message.lower()

    def test_storage_accounts_for_open_orders(self, db):
        """Storage check should account for incoming open orders."""
        # Open order for 600 units
        _create_test_po(db, quantity=600, status=PurchaseOrderStatus.OPEN)
        # New order for 300 units: 200 + 600 + 300 = 1100 > 1000
        po = _create_test_po(db, quantity=300)
        result = validate_purchase_order(db, po.id)
        storage_check = next(c for c in result.checks if c.name == "storage")
        assert storage_check.passed is False


# ---------------------------------------------------------------------------
# Supplier availability tests
# ---------------------------------------------------------------------------

class TestSupplierAvailabilityValidation:
    def test_supplier_availability_pass(self, db):
        """Order within supplier availability should pass."""
        po = _create_test_po(db, quantity=500)  # 500 < 2000 available
        result = validate_purchase_order(db, po.id)
        avail_check = next(c for c in result.checks if c.name == "supplier_availability")
        assert avail_check.passed is True

    def test_supplier_availability_fail(self, db):
        """Order exceeding supplier availability should fail."""
        po = _create_test_po(db, quantity=2500)  # 2500 > 2000 available
        result = validate_purchase_order(db, po.id)
        avail_check = next(c for c in result.checks if c.name == "supplier_availability")
        assert avail_check.passed is False


# ---------------------------------------------------------------------------
# Quantity tests
# ---------------------------------------------------------------------------

class TestQuantityValidation:
    def test_quantity_positive_pass(self, db):
        po = _create_test_po(db, quantity=100)
        result = validate_purchase_order(db, po.id)
        qty_check = next(c for c in result.checks if c.name == "quantity")
        assert qty_check.passed is True

    def test_quantity_zero_fail(self, db):
        po = _create_test_po(db, quantity=0)
        result = validate_purchase_order(db, po.id)
        qty_check = next(c for c in result.checks if c.name == "quantity")
        assert qty_check.passed is False


# ---------------------------------------------------------------------------
# Full validation tests
# ---------------------------------------------------------------------------

class TestFullValidation:
    def test_all_pass(self, db):
        """A valid order should pass all checks."""
        po = _create_test_po(db, quantity=500, unit_price=10.0)
        result = validate_purchase_order(db, po.id)
        assert result.passed is True
        assert all(c.passed for c in result.checks)

    def test_multiple_failures(self, db):
        """An invalid order can fail multiple checks simultaneously."""
        # quantity=50 (< MOQ 100), but fits budget/storage
        po = _create_test_po(db, quantity=50, unit_price=10.0)
        result = validate_purchase_order(db, po.id)
        assert result.passed is False
        failed = [c.name for c in result.checks if not c.passed]
        assert "moq" in failed

    def test_nonexistent_order(self, db):
        """Validating a nonexistent order should fail gracefully."""
        result = validate_purchase_order(db, 9999)
        assert result.passed is False
        assert result.checks[0].name == "order_exists"

    def test_proposed_order_validation(self, db):
        """validate_proposed_order works without persisting a PO."""
        result = validate_proposed_order(
            db, product_id=1, supplier_id=1, node_id=1,
            quantity=500, unit_price=10.0,
        )
        assert result.passed is True

    def test_proposed_order_fails_storage(self, db):
        """Proposed order that exceeds storage should fail."""
        result = validate_proposed_order(
            db, product_id=1, supplier_id=1, node_id=1,
            quantity=900, unit_price=10.0,
        )
        assert result.passed is False
        storage_check = next(c for c in result.checks if c.name == "storage")
        assert storage_check.passed is False
