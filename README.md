# AI Purchasing Agent

A full-stack AI purchasing system where an autonomous agent investigates purchasing situations, evaluates constraints using tool calls, makes decisions (ACCEPT/MODIFY/REJECT/INVESTIGATE), executes actions with human approval gates, and validates results through a deterministic feedback loop.

## Problem Statement

A retail/quick-commerce company manages purchasing of products from multiple suppliers across multiple fulfillment nodes. Buyers spend significant time manually reviewing purchasing information and making decisions about what, when, and how much to purchase.

This system demonstrates an **AI agent that can automate part of the buyer's workflow** — not as a chatbot that answers questions, but as a system capable of **making, executing, and validating purchasing decisions**.

## Solution

The AI Purchasing Agent:
1. **Investigates** a purchasing recommendation using tool calls (inventory, demand, suppliers, budget, storage)
2. **Reasons** about multiple constraints simultaneously
3. **Decides** whether to ACCEPT, MODIFY, REJECT, or INVESTIGATE FURTHER
4. **Explains** the decision with reasoning, important factors, and confidence level
5. **Executes** the action (creates/modifies purchase orders) when allowed
6. **Requests human approval** when the action exceeds risk thresholds
7. **Validates** the result using deterministic business rules
8. **Self-corrects** through a feedback loop when validation fails

## Architecture

![Architecture Diagram](docs/architecture-diagram.png)

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Google Gemini API with Native Function Calling** | Native tool-calling loop using the modern `google-genai` SDK without third-party agent wrapper overhead. |
| **Deterministic validation separate from LLM** | Business-critical constraints (budget, MOQ, storage) must never depend on LLM. The LLM *recommends*, the backend *validates*. |
| **Feedback loop** | If validation fails, the failure is fed back to the agent. The agent re-investigates and provides a corrected recommendation (up to 3 iterations). |
| **Agent activity log** | Every tool call is logged, enabling full observability of what the agent investigated and why. |
| **Human approval gate** | The agent flags when human oversight is needed (large orders, low-reliability suppliers, significant quantity changes). The system blocks execution until approved. |
| **No microservices, no Redis, no K8s** | A single FastAPI backend is sufficient. Complexity is in the agent logic, not the infrastructure. |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 18, TypeScript, Angular Material, SCSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL 16 |
| AI | Google Gemini API (`gemini-3.6-flash` / `gemini-3.7-flash`), native function calling via `google-genai` |
| Testing | Pytest (backend), mocked Gemini responses |
| Infrastructure | Docker Compose (PostgreSQL) |

## Agent Workflow

```
Recommendation received
         │
         ▼
┌─────────────────────┐
│  Agent Investigation │ ← Tool calls: inventory, demand,
│  (Gemini + Tools)    │   open POs, supplier, budget, storage
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Agent Decision     │ → ACCEPT / MODIFY / REJECT / INVESTIGATE
│   (Structured JSON)  │   + reasoning + confidence + factors
└─────────┬───────────┘
          │
    ┌─────┴──────┐
    │ Requires   │
    │ approval?  │
    ├─YES────────┤
    │            ▼
    │   ┌───────────────┐
    │   │ Human Approval │ → APPROVE / REJECT
    │   └───────┬───────┘
    │           │
    ├───────────┘
    │ NO
    ▼
┌─────────────────────┐
│ Create/Modify PO     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Deterministic        │ → Budget ✓  MOQ ✓  Storage ✓
│ Validation           │   Supplier ✓  Quantity ✓
└─────────┬───────────┘
          │
    ┌─────┴──────┐
    │   PASS?    │
    ├─YES────────┤──→ PO Finalized ✓
    │            │
    │ NO         │
    ▼            │
┌────────────┐   │
│ Feed back  │   │
│ to agent   │───┘ (max 3 iterations)
└────────────┘
```

## Available Tools

The AI agent can call these tools during investigation:

| Tool | Purpose |
|---|---|
| `get_product` | Product details (SKU, name, price) |
| `get_inventory` | Current stock at a fulfillment node |
| `get_demand_forecast` | Expected demand for upcoming period |
| `get_open_purchase_orders` | Existing open/active POs |
| `get_supplier_details` | Supplier MOQ, lead time, reliability |
| `get_alternative_suppliers` | Other suppliers for the same product |
| `get_budget` | Available budget at a node |
| `get_storage_capacity` | Remaining storage capacity |
| `calculate_purchase_quantity` | Net need = demand - inventory - open POs |

## Database Design

9 tables with clear relationships:
- **Master data**: Product, FulfillmentNode, Inventory, DemandForecast
- **Supplier data**: Supplier, SupplierProduct (many-to-many)
- **Transactions**: PurchaseOrder, Budget
- **Agent data**: PurchasingRecommendation, AgentDecision, AgentActivityLog

## Validation Strategy

Deterministic validation runs **after** the agent creates/modifies a PO:

1. **Quantity** — Must be positive
2. **MOQ** — Must meet supplier minimum order quantity
3. **Budget** — Total cost must not exceed remaining node budget
4. **Storage** — Projected inventory must fit within node capacity
5. **Supplier Availability** — Supplier must have sufficient stock
6. **PO Validity** — All required fields present

Each check returns PASS/FAIL with a human-readable message, actual value, and limit.

## Feedback Loop

If validation fails:
1. The failure details are sent back to the agent
2. The agent re-investigates constraints using tools
3. The agent provides a corrected recommendation
4. Validation runs again
5. Repeat up to 3 times
6. If still failing after 3 iterations, the PO is cancelled

The entire loop is visible in the UI's activity timeline.

## Human Approval Workflow

The agent flags actions for human approval when:
- Order value exceeds $10,000
- Quantity exceeds 500 units
- Supplier reliability is below 0.8
- Quantity change exceeds 30% from original recommendation

The buyer sees the full AI reasoning and can APPROVE, REJECT, or request RE-INVESTIGATION.

## Implemented Scenarios

### Scenario 1 — Purchase Recommendation Review (Primary)
- System recommends 800 units of Organic Almonds
- Agent investigates: inventory (120), demand (500), open POs (200), storage (1320 remaining), budget
- Agent calculates net need: 500 - 120 - 200 = 180 units
- Agent decides: **MODIFY** to 180 units
- Flags for human approval (>30% reduction)
- Buyer approves → PO created ($1,980.00)
- Deterministic validator runs: all 6 checks PASS ✓

### Scenario 2 — Supplier Cannot Fulfill (Secondary)
- PO for 500 units, supplier can only supply 250
- Agent investigates alternative suppliers
- Decides whether to split, modify, wait, or escalate

### Seed Data Scenarios
5 recommendations designed for different outcomes:

| # | Product | Qty | Expected | Why |
|---|---|---|---|---|
| 1 | Organic Almonds | 800 | MODIFY | Storage/net need adjustment |
| 2 | Cold Brew Coffee | 200 | MODIFY/ACCEPT | Net need calculated against inventory |
| 3 | Protein Bars | 1500 | REJECT | Budget insufficient |
| 4 | Fresh Orange Juice | 300 | ACCEPT | Straightforward replenishment |
| 5 | Coconut Water | 600 | INVESTIGATE | Low supplier reliability |

## Test Scenarios

All tests use **mocked Gemini responses** — no real API calls required for unit testing.

### Validation Tests (18 tests)
- Budget pass/fail, accounts for existing orders
- MOQ pass/fail
- Storage capacity pass/fail, accounts for incoming orders
- Supplier availability pass/fail
- Quantity positive check
- Full validation pass/fail
- Proposed (pre-creation) validation
- Nonexistent order handling

### Agent Tests (8 tests)
- Agent accepts valid recommendation
- Agent modifies when storage is limited
- Agent rejects when budget is impossible
- Human approval is required when flagged
- Feedback loop corrects validation failure
- JSON parsing (valid, code-block wrapped, invalid)

## Setup Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ / Docker

### Environment Variables

Copy `.env.example` to `backend/.env` and fill in:

```bash
cp .env.example backend/.env
```

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
DATABASE_URL=postgresql://purchasing_agent:purchasing_agent_dev@localhost:5432/purchasing_agent
LOG_LEVEL=INFO
```

### Running Backend

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Seed the database (if needed)
python -m app.database.seed

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Running Frontend

```bash
cd frontend
npm install
npx ng serve --port 4200
```

Open http://localhost:4200

### Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

## Example Demo Flow

1. Open http://localhost:4200 → Dashboard shows summary cards & pending recommendations
2. Navigate to Recommendations → Click recommendation #1 (Organic Almonds, 800 units)
3. Click "Run AI Review" → Watch the agent investigate:
   - ✓ Inventory checked (120 units)
   - ✓ Demand forecast checked (500 units)
   - ✓ Open PO checked (200 units incoming)
   - ✓ Storage checked (1,320 capacity remaining)
   - ✓ Budget checked ($47,800 remaining)
   - ✓ Supplier checked (NutriSource MX)
4. See AI Decision: **MODIFY** → 180 units (satisfies net need 500 - 120 - 200 = 180)
5. See reasoning, important factors, and constraints checked
6. Human approval required badge is displayed
7. Click "Approve Purchase" → Purchase Order #4 is created ($1,980.00)
8. See Validation Result: all 6 checks PASS ✓

## Project Structure

```
ai-purchasing-agent/
├── frontend/                    # Angular 18 app (Material UI)
│   └── src/app/
│       ├── core/services/       # API service (PurchasingService)
│       ├── core/models/         # TypeScript interfaces
│       └── features/
│           ├── dashboard/       # Summary stats + recommendations table
│           ├── recommendations/ # List + detail (main demo page)
│           ├── purchase-orders/ # PO management
│           ├── suppliers/       # Supplier list
│           └── inventory/       # Stock levels
├── backend/
│   └── app/
│       ├── api/                 # FastAPI route handlers
│       ├── agent/               # Gemini orchestrator + prompts
│       ├── models/              # SQLAlchemy models
│       ├── schemas/             # Pydantic schemas
│       ├── tools/               # Agent tools (Gemini Function Declarations)
│       ├── validation/          # Deterministic validation engine
│       └── database/            # DB session + seed data
├── tests/                       # Pytest test suite (26 tests)
├── docs/                        # Architecture documentation + diagrams
├── docker-compose.yml           # PostgreSQL container
├── .env.example                 # Environment template
└── README.md
```
