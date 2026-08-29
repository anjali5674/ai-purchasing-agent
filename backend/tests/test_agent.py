"""
Tests for the AI Agent — using mocked Google Gemini responses.

These tests verify agent behavior without making real API calls:
1. Agent accepts when all constraints pass
2. Agent modifies when constraints require adjustment
3. Agent rejects when purchase is impossible
4. Feedback loop corrects failed validation
5. Human approval is required for appropriate actions

All Gemini responses are mocked with deterministic tool calls and decisions.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.models import (
    Product, FulfillmentNode, Inventory, DemandForecast,
    Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderStatus,
    Budget, PurchasingRecommendation, RecommendationStatus,
)
from app.agent.orchestrator import review_recommendation, _parse_decision


from app.config import get_settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.agent.orchestrator.get_settings") as mock_set:
        s = MagicMock()
        s.gemini_api_key = "test-mock-gemini-key"
        s.gemini_model = "gemini-3.6-flash"
        mock_set.return_value = s
        yield s


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    _seed_test_data(session)
    yield session
    session.close()


def _seed_test_data(db):
    db.add(Product(id=1, sku="TEST-001", name="Test Product", category="Test", unit_price=10.0))
    db.add(FulfillmentNode(id=1, name="Test Node", location="Test", storage_capacity=1000))
    db.add(Inventory(product_id=1, node_id=1, current_quantity=200))
    db.add(DemandForecast(product_id=1, node_id=1, forecast_quantity=500, forecast_period="2026-Q4"))
    db.add(Supplier(
        id=1, name="Test Supplier",
        lead_time_days=5, minimum_order_quantity=100,
        available_quantity=2000, reliability_score=0.95,
    ))
    db.add(SupplierProduct(supplier_id=1, product_id=1, unit_price=10.0))
    db.add(Budget(node_id=1, available_amount=50000.0))
    db.commit()


def _create_recommendation(db, quantity=500, status=RecommendationStatus.PENDING):
    rec = PurchasingRecommendation(
        product_id=1, node_id=1, supplier_id=1,
        recommended_quantity=quantity, status=status,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


# ---------------------------------------------------------------------------
# Helper: mock Gemini client
# ---------------------------------------------------------------------------

def _mock_gemini_response(decision_json: dict, tool_calls_before: list | None = None):
    """
    Create a mock Gemini client that:
    1. Optionally makes tool calls (investigation)
    2. Returns a final decision JSON
    """
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    responses = []

    # If tool calls are specified, add a tool call response first
    if tool_calls_before:
        tool_response = MagicMock()
        tool_response.function_calls = tool_calls_before
        tool_response.text = None
        responses.append(tool_response)

    # Final decision response
    final_response = MagicMock()
    final_response.function_calls = None
    final_response.text = json.dumps(decision_json)
    responses.append(final_response)

    mock_chat.send_message.side_effect = responses
    return mock_client


def _make_tool_call(tool_name: str, arguments: dict):
    tc = MagicMock()
    tc.name = tool_name
    tc.args = arguments
    return tc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseDecision:
    def test_valid_json(self):
        result = _parse_decision('{"decision": "ACCEPT", "reasoning": "OK", "confidence": "HIGH"}')
        assert result["decision"] == "ACCEPT"

    def test_json_in_code_block(self):
        content = '```json\n{"decision": "MODIFY", "reasoning": "Adjusted", "confidence": "MEDIUM"}\n```'
        result = _parse_decision(content)
        assert result["decision"] == "MODIFY"

    def test_invalid_json_returns_investigate(self):
        result = _parse_decision("This is not JSON")
        assert result["decision"] == "INVESTIGATE"
        assert result["confidence"] == "LOW"


class TestAgentAccept:
    @patch("app.agent.orchestrator.genai.Client")
    def test_agent_accepts_valid_recommendation(self, mock_client_cls, db):
        rec = _create_recommendation(db, quantity=300)

        decision = {
            "decision": "ACCEPT",
            "suggested_quantity": 300,
            "reasoning": "All constraints pass. Demand justifies purchase.",
            "important_factors": ["Demand exceeds inventory", "Budget sufficient"],
            "constraints_checked": ["inventory", "demand", "budget", "storage", "supplier"],
            "confidence": "HIGH",
            "requires_human_approval": False,
        }

        mock_client = _mock_gemini_response(decision, tool_calls_before=[
            _make_tool_call("get_inventory", {"product_id": 1, "node_id": 1}),
            _make_tool_call("get_budget", {"node_id": 1}),
        ])
        mock_client_cls.return_value = mock_client

        result = review_recommendation(db, rec.id)

        assert result["decision"]["decision"] == "ACCEPT"
        assert result["decision"]["suggested_quantity"] == 300


class TestAgentModify:
    @patch("app.agent.orchestrator.genai.Client")
    def test_agent_modifies_when_storage_limited(self, mock_client_cls, db):
        rec = _create_recommendation(db, quantity=900)

        decision = {
            "decision": "MODIFY",
            "suggested_quantity": 500,
            "reasoning": "Reduced quantity to fit storage capacity.",
            "important_factors": ["Storage capacity exceeded at 900 units"],
            "constraints_checked": ["inventory", "storage"],
            "confidence": "HIGH",
            "requires_human_approval": True,
        }

        mock_client = _mock_gemini_response(decision)
        mock_client_cls.return_value = mock_client

        result = review_recommendation(db, rec.id)

        assert result["decision"]["decision"] == "MODIFY"
        assert result["decision"]["suggested_quantity"] == 500


class TestAgentReject:
    @patch("app.agent.orchestrator.genai.Client")
    def test_agent_rejects_when_impossible(self, mock_client_cls, db):
        rec = _create_recommendation(db, quantity=1500)

        decision = {
            "decision": "REJECT",
            "suggested_quantity": None,
            "reasoning": "Budget insufficient for this quantity.",
            "important_factors": ["Budget would be exceeded"],
            "constraints_checked": ["budget"],
            "confidence": "HIGH",
            "requires_human_approval": False,
        }

        mock_client = _mock_gemini_response(decision)
        mock_client_cls.return_value = mock_client

        result = review_recommendation(db, rec.id)

        assert result["decision"]["decision"] == "REJECT"
        assert result["purchase_order"] is None


class TestHumanApproval:
    @patch("app.agent.orchestrator.genai.Client")
    def test_human_approval_required(self, mock_client_cls, db):
        rec = _create_recommendation(db, quantity=800)

        decision = {
            "decision": "MODIFY",
            "suggested_quantity": 600,
            "reasoning": "Adjusted quantity but requires human review.",
            "important_factors": ["Large order value"],
            "constraints_checked": ["budget", "storage"],
            "confidence": "MEDIUM",
            "requires_human_approval": True,
        }

        mock_client = _mock_gemini_response(decision)
        mock_client_cls.return_value = mock_client

        result = review_recommendation(db, rec.id)

        assert result["decision"]["requires_human_approval"] == 1
        # PO should NOT be created when approval is required
        assert result["purchase_order"] is None

        # Status should be PENDING_APPROVAL
        db.refresh(rec)
        assert rec.status == RecommendationStatus.PENDING_APPROVAL


class TestFeedbackLoop:
    @patch("app.agent.orchestrator.genai.Client")
    def test_validation_failure_triggers_reinvestigation(self, mock_client_cls, db):
        """
        Simulate: agent recommends 900 → validation fails (storage) →
        agent re-investigates → corrects to 500 → validation passes.
        """
        rec = _create_recommendation(db, quantity=900)

        # First attempt: 900 units (will fail storage)
        initial_decision = {
            "decision": "ACCEPT",
            "suggested_quantity": 900,
            "reasoning": "Initial recommendation.",
            "important_factors": [],
            "constraints_checked": ["inventory"],
            "confidence": "HIGH",
            "requires_human_approval": False,
        }

        # After feedback: corrected to 500
        corrected_decision = {
            "decision": "MODIFY",
            "suggested_quantity": 500,
            "reasoning": "Reduced to fit storage capacity.",
            "important_factors": ["Storage capacity corrected"],
            "constraints_checked": ["inventory", "storage"],
            "confidence": "HIGH",
            "requires_human_approval": False,
        }

        # Mock: first call returns initial, second call returns corrected
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        responses = []
        for decision in [initial_decision, corrected_decision]:
            resp = MagicMock()
            resp.function_calls = None
            resp.text = json.dumps(decision)
            responses.append(resp)

        mock_chat.send_message.side_effect = responses
        mock_client_cls.return_value = mock_client

        result = review_recommendation(db, rec.id)

        # Should have gone through feedback loop
        assert result["feedback_iterations"] >= 1
        # Final validation should pass
        assert result["validation"]["passed"] is True
        # Final quantity should be 500
        assert result["purchase_order"]["quantity"] == 500
