"""
Agent Orchestrator — the core AI loop powered by Google Gemini.

Workflow:
1. Receive a recommendation to review
2. Build context message with recommendation details
3. Send to Google Gemini with tool definitions
4. Loop: process tool calls → return results as function responses → repeat until final decision
5. Parse structured decision
6. Store AgentDecision
7. If ACCEPT/MODIFY: create/modify PO → validate → feedback loop if needed
8. Return result

The orchestrator handles the Gemini API interaction and the feedback loop.
It does NOT contain business logic — that lives in the validation engine and tools.
"""

import json
import logging
import time
from datetime import datetime, timezone

from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types, errors
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.models import (
    PurchasingRecommendation, RecommendationStatus,
    AgentDecision, AgentDecisionType, ConfidenceLevel,
    AgentActivityLog,
    PurchaseOrder, PurchaseOrderStatus,
)
from app.tools.purchasing_tools import get_gemini_tools, execute_tool
from app.validation.validator import validate_purchase_order, validate_proposed_order
from app.agent.prompts import SYSTEM_PROMPT, FEEDBACK_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

MAX_FEEDBACK_ITERATIONS = 3
MAX_TOOL_CALL_ROUNDS = 10  # Safety limit on tool call loops


def _log_activity(db: Session, recommendation_id: int, event_type: str, event_data: dict | None = None):
    db.add(AgentActivityLog(
        recommendation_id=recommendation_id,
        event_type=event_type,
        event_data=event_data,
        timestamp=datetime.now(timezone.utc),
    ))
    db.flush()


def review_recommendation(db: Session, recommendation_id: int, context: str | None = None) -> dict:
    """
    Main entry point: run the AI agent to review a purchasing recommendation.

    Returns a dict with the decision, validation result, and any created PO.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured in backend/.env. Please configure a valid Google Gemini API key.")

    recommendation = (
        db.query(PurchasingRecommendation)
        .filter(PurchasingRecommendation.id == recommendation_id)
        .first()
    )
    if not recommendation:
        raise ValueError(f"Recommendation {recommendation_id} not found")

    # Update status
    recommendation.status = RecommendationStatus.UNDER_REVIEW
    db.flush()

    _log_activity(db, recommendation_id, "investigation_started", {
        "recommendation_id": recommendation_id,
        "recommended_quantity": recommendation.recommended_quantity,
    })

    # Build initial user message with recommendation context and candidate suppliers
    user_message = _build_user_message(db, recommendation, context)

    # Initialize Gemini client
    client = genai.Client(api_key=settings.gemini_api_key)

    # Run the agent loop
    decision_data = _run_agent_loop(
        client=client,
        db=db,
        recommendation=recommendation,
        user_message=user_message,
        model=settings.gemini_model,
    )

    # Store the decision
    agent_decision = _store_decision(db, recommendation, decision_data)

    _log_activity(db, recommendation_id, "decision_generated", {
        "decision": decision_data.get("decision"),
        "suggested_quantity": decision_data.get("suggested_quantity"),
        "confidence": decision_data.get("confidence"),
    })

    result = {
        "recommendation_id": recommendation_id,
        "decision": _decision_to_response(agent_decision),
        "validation": None,
        "purchase_order": None,
        "feedback_iterations": 0,
    }

    # If ACCEPT or MODIFY, attempt to create/modify PO and validate
    if decision_data["decision"] in ("ACCEPT", "MODIFY"):
        result = _execute_and_validate(
            client=client,
            db=db,
            recommendation=recommendation,
            decision_data=decision_data,
            result=result,
            model=settings.gemini_model,
        )

    # Update recommendation status
    _update_recommendation_status(db, recommendation, decision_data, agent_decision)
    db.commit()

    return result


def _build_user_message(db: Session, recommendation: PurchasingRecommendation, context: str | None) -> str:
    """Build the initial user message with recommendation details and candidate suppliers."""
    from app.models.models import Supplier, SupplierProduct

    msg = (
        f"Please review the following purchasing recommendation:\n\n"
        f"- Recommendation ID: {recommendation.id}\n"
        f"- Product ID: {recommendation.product_id}\n"
        f"- Fulfillment Node ID: {recommendation.node_id}\n"
        f"- Recommended Quantity: {recommendation.recommended_quantity}\n"
    )

    if recommendation.supplier_id:
        s1 = db.query(Supplier).filter(Supplier.id == recommendation.supplier_id).first()
        sp1 = db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == recommendation.supplier_id,
            SupplierProduct.product_id == recommendation.product_id,
        ).first()
        if s1:
            price_str = f"${sp1.unit_price:.2f}" if sp1 else "N/A"
            msg += (
                f"- Candidate Supplier 1: ID {s1.id} ({s1.name}) | Price: {price_str} | "
                f"Lead Time: {s1.lead_time_days} days | MOQ: {s1.minimum_order_quantity} | "
                f"Available: {s1.available_quantity} | Reliability: {int(s1.reliability_score * 100)}%\n"
            )

    if recommendation.secondary_supplier_id:
        s2 = db.query(Supplier).filter(Supplier.id == recommendation.secondary_supplier_id).first()
        sp2 = db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == recommendation.secondary_supplier_id,
            SupplierProduct.product_id == recommendation.product_id,
        ).first()
        if s2:
            price_str = f"${sp2.unit_price:.2f}" if sp2 else "N/A"
            msg += (
                f"- Candidate Supplier 2: ID {s2.id} ({s2.name}) | Price: {price_str} | "
                f"Lead Time: {s2.lead_time_days} days | MOQ: {s2.minimum_order_quantity} | "
                f"Available: {s2.available_quantity} | Reliability: {int(s2.reliability_score * 100)}%\n"
            )

    if context:
        msg += f"\nAdditional context: {context}\n"

    msg += (
        "\nPlease investigate this recommendation using the available tools. "
        "Compare both candidate suppliers across all dimensions (pricing, lead time, MOQ, available stock, reliability). "
        "Select the optimal supplier (populate selected_supplier_id, supplier_selection_reason, and supplier_comparison), "
        "evaluate inventory, demand, open POs, budget, and storage capacity, then provide your final decision."
    )
    return msg


def _send_chat_message_with_retry(chat, message, max_retries: int = 4):
    """Send a message to the Gemini chat session with exponential backoff on transient errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return chat.send_message(message)
        except errors.APIError as e:
            err_code = getattr(e, "code", None)
            err_text = str(e).lower()
            is_rate_limit = err_code == 429 or "quota" in err_text or "rate-limit" in err_text
            is_unavailable = err_code == 503 or "unavailable" in err_text

            if (is_unavailable or is_rate_limit) and attempt < max_retries:
                wait_sec = 8.0 * attempt if is_rate_limit else 2.5 * attempt
                logger.warning(f"Gemini API notice ({err_code}). Waiting {wait_sec:.1f}s for quota window (attempt {attempt}/{max_retries})...")
                time.sleep(wait_sec)
                continue

            err_msg = getattr(e, "message", str(e))
            if is_rate_limit:
                raise RuntimeError("Gemini API rate limit reached on free tier. Please wait a moment and try again.") from e
            elif is_unavailable:
                raise RuntimeError("Gemini AI service is temporarily experiencing high traffic. Please retry in a few seconds.") from e
            else:
                logger.error(f"Gemini API Error ({err_code}): {err_msg}")
                raise RuntimeError(f"Gemini API error: {err_msg}") from e
        except Exception as e:
            if attempt < max_retries and ("connection" in str(e).lower() or "timeout" in str(e).lower()):
                wait_sec = 3.0 * attempt
                logger.warning(f"Gemini connection issue: {e}. Retrying in {wait_sec}s...")
                time.sleep(wait_sec)
                continue
            logger.error(f"Gemini unexpected error ({type(e).__name__}): {e}")
            raise RuntimeError(f"AI service temporarily unavailable: {str(e)}") from e


def _run_agent_loop(
    client: genai.Client,
    db: Session,
    recommendation: PurchasingRecommendation,
    user_message: str,
    model: str,
) -> dict:
    """Run the Gemini tool-calling loop until the agent returns a final decision."""
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=get_gemini_tools(),
        temperature=0.1,
    )

    chat = client.chats.create(model=model, config=config)
    response = _send_chat_message_with_retry(chat, user_message)

    for round_num in range(MAX_TOOL_CALL_ROUNDS):
        # Check if the model called any tools
        if response.function_calls:
            function_responses = []

            for call in response.function_calls:
                tool_name = call.name
                arguments = dict(call.args) if call.args else {}

                logger.info(f"Agent calling tool: {tool_name}({arguments})")

                tool_result = execute_tool(
                    db=db,
                    recommendation_id=recommendation.id,
                    tool_name=tool_name,
                    arguments=arguments,
                )

                resp_payload = tool_result if isinstance(tool_result, dict) else {"result": tool_result}
                function_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response=resp_payload,
                    )
                )

            # Send function execution results back to the model with retry
            response = _send_chat_message_with_retry(chat, function_responses)
            continue

        # Final response — parse the decision JSON
        content = response.text or ""
        return _parse_decision(content)

    # Safety: if we hit the round limit, return a default
    logger.warning("Agent hit max tool call rounds, returning INVESTIGATE")
    return {
        "decision": "INVESTIGATE",
        "suggested_quantity": None,
        "reasoning": "Agent investigation reached maximum rounds. Manual review recommended.",
        "important_factors": ["Investigation limit reached"],
        "constraints_checked": [],
        "confidence": "LOW",
        "requires_human_approval": True,
    }


def _parse_decision(content: str) -> dict:
    """Parse the agent's final response as a JSON decision."""
    # Try to extract JSON from the content (handle markdown code blocks)
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Remove markdown code fences
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse agent response as JSON: {content[:200]}")
        decision = {
            "decision": "INVESTIGATE",
            "suggested_quantity": None,
            "reasoning": f"Agent response could not be parsed. Raw: {content[:500]}",
            "important_factors": ["Parse error"],
            "constraints_checked": [],
            "confidence": "LOW",
            "requires_human_approval": True,
        }

    # Validate required fields
    required = ["decision", "reasoning", "confidence"]
    for field in required:
        if field not in decision:
            decision[field] = "INVESTIGATE" if field == "decision" else "Unknown"

    return decision


def _store_decision(db: Session, recommendation: PurchasingRecommendation, decision_data: dict) -> AgentDecision:
    """Persist an agent decision to the database."""
    selected_sup_id = decision_data.get("selected_supplier_id") or recommendation.supplier_id
    decision = AgentDecision(
        recommendation_id=recommendation.id,
        decision=AgentDecisionType(decision_data["decision"]),
        suggested_quantity=decision_data.get("suggested_quantity"),
        selected_supplier_id=selected_sup_id,
        supplier_selection_reason=decision_data.get("supplier_selection_reason"),
        supplier_comparison=decision_data.get("supplier_comparison"),
        reasoning=decision_data["reasoning"],
        important_factors=decision_data.get("important_factors", []),
        constraints_checked=decision_data.get("constraints_checked", []),
        confidence=ConfidenceLevel(decision_data.get("confidence", "MEDIUM")),
        requires_human_approval=1 if decision_data.get("requires_human_approval", False) else 0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(decision)
    db.flush()
    return decision


def _execute_and_validate(
    client: genai.Client,
    db: Session,
    recommendation: PurchasingRecommendation,
    decision_data: dict,
    result: dict,
    model: str,
) -> dict:
    """Create/modify a PO, validate it, and run the feedback loop if needed."""
    quantity = decision_data.get("suggested_quantity") or recommendation.recommended_quantity
    supplier_id = decision_data.get("selected_supplier_id") or recommendation.supplier_id or 1

    # Get unit price from supplier-product mapping
    from app.models.models import SupplierProduct
    sp = (
        db.query(SupplierProduct)
        .filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == recommendation.product_id,
        )
        .first()
    )
    unit_price = sp.unit_price if sp else 10.0

    # Check if human approval is required
    if decision_data.get("requires_human_approval"):
        recommendation.status = RecommendationStatus.PENDING_APPROVAL
        _log_activity(db, recommendation.id, "human_approval_requested", {
            "quantity": quantity,
            "supplier_id": supplier_id,
            "reason": "Agent flagged this decision for human approval",
        })
        result["decision"]["requires_human_approval"] = 1
        db.flush()
        return result

    # Create the purchase order
    po = PurchaseOrder(
        product_id=recommendation.product_id,
        supplier_id=supplier_id,
        node_id=recommendation.node_id,
        quantity=quantity,
        unit_price=unit_price,
        total_price=quantity * unit_price,
        status=PurchaseOrderStatus.DRAFT,
        created_at=datetime.now(timezone.utc),
    )
    db.add(po)
    db.flush()

    _log_activity(db, recommendation.id, "purchase_order_created", {
        "po_id": po.id,
        "quantity": quantity,
        "total_price": po.total_price,
    })

    # Validate
    validation = validate_purchase_order(db, po.id)
    _log_activity(db, recommendation.id,
                  "validation_passed" if validation.passed else "validation_failed",
                  {"checks": [c.model_dump() for c in validation.checks]})

    result["validation"] = validation.model_dump()
    result["purchase_order"] = {
        "id": po.id,
        "product_id": po.product_id,
        "supplier_id": po.supplier_id,
        "node_id": po.node_id,
        "quantity": po.quantity,
        "unit_price": po.unit_price,
        "total_price": po.total_price,
        "status": po.status.value,
        "created_at": po.created_at.isoformat() if po.created_at else None,
    }

    # Feedback loop
    iteration = 0
    while not validation.passed and iteration < MAX_FEEDBACK_ITERATIONS:
        iteration += 1
        result["feedback_iterations"] = iteration

        _log_activity(db, recommendation.id, "agent_re_investigating", {
            "iteration": iteration,
            "failures": [c.name for c in validation.checks if not c.passed],
        })

        # Feed validation failures back to the agent
        feedback_msg = FEEDBACK_PROMPT_TEMPLATE.format(
            validation_result=json.dumps([c.model_dump() for c in validation.checks], indent=2)
        )

        new_decision = _run_agent_loop(
            client=client,
            db=db,
            recommendation=recommendation,
            user_message=feedback_msg,
            model=model,
        )

        new_quantity = new_decision.get("suggested_quantity")
        if new_quantity and new_quantity != po.quantity:
            po.quantity = new_quantity
            po.total_price = new_quantity * po.unit_price
            db.flush()

            _log_activity(db, recommendation.id, "purchase_order_modified", {
                "po_id": po.id,
                "new_quantity": new_quantity,
                "new_total_price": po.total_price,
                "iteration": iteration,
            })

        # Store the corrected decision
        _store_decision(db, recommendation, new_decision)

        # Re-validate
        validation = validate_purchase_order(db, po.id)
        _log_activity(db, recommendation.id,
                      "validation_passed" if validation.passed else "validation_failed",
                      {"checks": [c.model_dump() for c in validation.checks], "iteration": iteration})

        result["validation"] = validation.model_dump()
        result["decision"] = _decision_to_response(
            _store_decision(db, recommendation, new_decision)
        ) if not validation.passed else result["decision"]
        result["purchase_order"]["quantity"] = po.quantity
        result["purchase_order"]["total_price"] = po.total_price

    # Finalize PO status
    if validation.passed:
        po.status = PurchaseOrderStatus.OPEN
        _log_activity(db, recommendation.id, "purchase_order_finalized", {
            "po_id": po.id, "status": "OPEN",
        })
    else:
        po.status = PurchaseOrderStatus.CANCELLED
        _log_activity(db, recommendation.id, "purchase_order_cancelled", {
            "po_id": po.id,
            "reason": "Validation failed after maximum feedback iterations",
        })

    db.flush()
    result["purchase_order"]["status"] = po.status.value
    return result


def _update_recommendation_status(
    db: Session,
    recommendation: PurchasingRecommendation,
    decision_data: dict,
    agent_decision: AgentDecision,
):
    """Update the recommendation status based on the decision."""
    if recommendation.status == RecommendationStatus.PENDING_APPROVAL:
        return  # Don't overwrite pending approval

    status_map = {
        "ACCEPT": RecommendationStatus.ACCEPTED,
        "MODIFY": RecommendationStatus.MODIFIED,
        "REJECT": RecommendationStatus.REJECTED,
        "INVESTIGATE": RecommendationStatus.INVESTIGATING,
    }
    recommendation.status = status_map.get(
        decision_data["decision"],
        RecommendationStatus.INVESTIGATING,
    )
    db.flush()


def _decision_to_response(decision: AgentDecision) -> dict:
    """Convert an AgentDecision model to a response dict."""
    return {
        "id": decision.id,
        "recommendation_id": decision.recommendation_id,
        "decision": decision.decision.value,
        "suggested_quantity": decision.suggested_quantity,
        "selected_supplier_id": decision.selected_supplier_id,
        "supplier_selection_reason": decision.supplier_selection_reason,
        "supplier_comparison": decision.supplier_comparison,
        "reasoning": decision.reasoning,
        "important_factors": decision.important_factors,
        "constraints_checked": decision.constraints_checked,
        "confidence": decision.confidence.value,
        "requires_human_approval": decision.requires_human_approval,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }
