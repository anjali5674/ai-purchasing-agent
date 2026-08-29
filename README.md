# AI Purchasing Agent

An autonomous, full-stack purchasing decision system that investigates procurement recommendations using Google Gemini function calling, evaluates multi-dimensional business constraints, generates structured purchasing decisions, enforces human approval gates, executes purchase orders, and validates outcomes through a deterministic feedback loop.

---

## 📌 Problem Overview

In modern retail and quick-commerce operations, purchasing teams manage thousands of fast-moving SKUs across multiple fulfillment centers and suppliers. Traditional enterprise replenishment systems generate automated reorder suggestions based on isolated statistical models, but these suggestions frequently fail to account for real-time operational constraints such as:

- Rapidly changing warehouse storage capacities
- Node-specific budget constraints
- Supplier Minimum Order Quantities (MOQ) and lead times
- Supplier stock availability and historical reliability
- Incoming stock from existing open purchase orders

Buyers spend significant time manually gathering context across disconnected ERP screens. This system demonstrates an **autonomous AI Purchasing Agent** that replaces manual data lookup and calculation with an **investigative, constraint-aware, and self-validating workflow**.

---

## 🏗️ System Architecture

![Architecture Diagram](docs/architecture-diagram.png)

The application is structured into four decoupled layers:

1. **Frontend (Angular 18 & SCSS):** Interactive buyer dashboard featuring real-time KPI summary cards, a recommendation review workspace, an AI Investigation Timeline visualizing step-by-step tool invocations, an interactive human approval modal, and purchase order tracking.
2. **Backend (FastAPI & Python 3.12):** High-performance async REST API orchestrating the agent execution lifecycle, exposing database CRUD endpoints, and driving deterministic business validation.
3. **AI Agent Core (Google Gemini & Native Function Calling):** Autonomous reasoning loop built on the official `google-genai` SDK (`gemini-3.6-flash`). The agent queries PostgreSQL via structured tool declarations to investigate business context before synthesizing decisions.
4. **Deterministic Validation Engine (SQLAlchemy & PostgreSQL):** An independent verification layer outside the LLM that verifies business-critical constraints before purchase orders are committed.

```
┌────────────────────────────────────────────────────────┐
│                   Angular 18 Frontend                  │
│   (Dashboard, Recommendations, POs, Timeline, UI)      │
└───────────────────────────┬────────────────────────────┘
                            │ REST API (JSON)
┌───────────────────────────▼────────────────────────────┐
│                    FastAPI Backend                     │
│   (Route Handlers, State Machine, Activity Logger)     │
└───────────────┬────────────────────────────┬───────────┘
                │                            │
┌───────────────▼──────────────┐  ┌──────────▼───────────┐
│       AI Purchasing Agent    │  │     Deterministic    │
│   (Google Gemini Orchestrator│  │   Validation Engine  │
│    + Function Calling Tools) │  │  (6 Business Checks) │
└───────────────┬──────────────┘  └──────────┬───────────┘
                │                            │
┌───────────────▼────────────────────────────▼───────────┐
│                 PostgreSQL 16 Database                 │
│  (Products, Suppliers, Inventory, Forecasts, POs, Log) │
└────────────────────────────────────────────────────────┘
```

---

## 🔄 Agent & Validation Lifecycle

```
Purchase Recommendation Received
               │
               ▼
┌──────────────────────────────┐
│     Agent Investigation      │ ◄── Tool Calls: Inventory, Forecasts,
│    (Gemini Function Calling) │     Open POs, Suppliers, Budget, Storage
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Structured Agent Decision   │ ──► ACCEPT / MODIFY / REJECT / INVESTIGATE
│      (JSON Schema Output)    │     + Suggested Qty, Confidence, Reasoning
└──────────────┬───────────────┘
               │
         ┌─────┴──────┐
         │ Requires   │
         │ Human Gate?│
         ├─ YES ──────┤
         │            ▼
         │   ┌──────────────────┐
         │   │  Human Approval  │ ──► APPROVE / REJECT
         │   └────────┬─────────┘
         │            │ (Approved)
         ├────────────┘
         │ NO
         ▼
┌──────────────────────────────┐
│     Create / Modify PO       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Deterministic Validation   │ ──► Quantity ✓  MOQ ✓  Budget ✓
│    (6 Independent Checks)    │     Storage ✓  Availability ✓  Validity ✓
└──────────────┬───────────────┘
               │
         ┌─────┴──────┐
         │   PASS?    │
         ├─ YES ──────┤ ──► Purchase Order Finalized ✓
         │            │
         │ NO         │
         ▼            │
┌──────────────────┐  │
│  Feedback Loop   │  │
│ (Retry Re-eval)  ├──┘ (Max 3 iterations)
└──────────────────┘
```

---

## 🛠️ Tech Stack

| Domain | Technology | Purpose |
|---|---|---|
| **Frontend** | Angular 18, TypeScript, SCSS, RxJS | Single-page application, reactive state management, investigation timeline |
| **Backend** | Python 3.12, FastAPI, Pydantic v2 | Async REST API, agent lifecycle management, schema enforcement |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 | Relational persistence, transactional safety, foreign key constraints |
| **AI / LLM** | Google Gemini API (`gemini-3.6-flash`), `google-genai` SDK | Native function calling, dynamic tool dispatching, structured reasoning |
| **Testing** | Pytest, Pytest-Asyncio, SQLite StaticPool | Automated test suite (32 unit & integration tests) |
| **Containerization** | Docker, Docker Compose | PostgreSQL local environment container |

---

## 🧰 Agent Investigation Tools

The agent interacts with the database exclusively through structured function declarations:

| Tool Function | Description | Return Payload |
|---|---|---|
| `get_product(product_id)` | Fetches master catalog data for a product | SKU, name, unit price, category, unit of measure |
| `get_inventory(product_id, node_id)` | Queries current on-hand stock at a fulfillment node | Available physical inventory quantity |
| `get_demand_forecast(product_id, node_id)` | Retrieves forecasted customer demand for the period | Forecasted demand quantity, period label |
| `get_open_purchase_orders(product_id, node_id)` | Fetches incoming stock from active, unfulfilled POs | List of active orders and total incoming units |
| `get_supplier_details(supplier_id)` | Inspects primary supplier contract parameters | Unit price, MOQ, lead time days, reliability score, stock |
| `get_alternative_suppliers(product_id)` | Discovers alternative suppliers stocking the SKU | List of suppliers with pricing, MOQ, lead time, and reliability |
| `get_budget(node_id)` | Retrieves the fulfillment center's available budget | Node budget cap, current committed spend, available amount |
| `get_storage_capacity(node_id)` | Calculates physical warehouse space availability | Total capacity, current utilization, remaining space |
| `calculate_purchase_quantity(product_id, node_id)` | Deterministically computes net demand requirement | Net Need = $\text{Forecast} - \text{Inventory} - \text{Open POs}$ |

---

## 📋 Assessment Scenarios Implementation

The project implements the scenarios outlined in the technical specification:

| Scenario | Business Problem | Implementation Status | Implementation Mechanism |
|---|---|---|---|
| **Scenario 1** | **Purchase Recommendation Review** | **Fully Implemented** | Full end-to-end flow: 800-unit recommendation analyzed across 8 tools &rarr; net need calculated (180 units) &rarr; `MODIFY` decision &rarr; human approval gate &rarr; PO created &rarr; 6 validation checks pass. |
| **Scenario 2** | **Supplier Cannot Fulfil Purchase** | **Partially Implemented** | Agent calls `get_supplier_details` and `get_alternative_suppliers` to detect stock deficits/low reliability and evaluate alternative vendors during recommendation review. *(See limitations)* |
| **Scenario 3** | **Demand / Forecast Has Changed** | **Partially Implemented** | Dynamic net-need calculation ($\text{Forecast} - \text{Stock} - \text{Open POs}$) updates purchase plans when recommendations are reviewed against current demand tables. *(See limitations)* |
| **Scenario 4** | **Purchasing Constraints** | **Fully Implemented** | Multi-constraint evaluation (Storage, Budget, MOQ, Supplier Stock) with 6-point deterministic validation, automatic quantity scaling, and self-correcting feedback loop. |

---

### Scenario 1 — Purchase Recommendation Review (Deep Dive)
- **Context:** An upstream statistical engine generates a purchase recommendation to buy **800 units** of *Organic Almonds 500g* (Product #1) for *Downtown Hub* (Node #1).
- **Investigation:** The agent does not blindly approve the recommendation. It calls investigation tools to collect real-time data:
  - Forecast Demand = **500 units**
  - Current On-Hand Inventory = **120 units**
  - Incoming Open Purchase Orders = **200 units**
  - Available Storage Capacity = **1,200 units**
  - Available Node Budget = **$50,000.00**
  - Primary Supplier (NutriSource MX) MOQ = **100 units**
- **Net Calculation:**
  $$\text{Net Need} = \text{Forecast Demand} (500) - \text{Current Stock} (120) - \text{Open POs} (200) = \mathbf{180\text{ units}}$$
- **Structured Outcome:**
  - **Decision:** `MODIFY`
  - **Suggested Quantity:** `180 units`
  - **Reasoning:** 800 units exceeds net demand requirements. 180 units satisfies customer demand, meets supplier MOQ (100), and respects storage and budget.
  - **Human Approval Flagged:** `TRUE` (77.5% reduction exceeds the 30% modification threshold).
- **Execution & Validation:** Buyer clicks "Approve" &rarr; Purchase Order #4 is created ($1,980.00) &rarr; Deterministic Validator passes all 6 checks &rarr; PO is finalized.

---

### Scenario 2 — Supplier Cannot Fulfil Purchase (Deep Dive)
- **Implemented Behavior:** When the primary supplier has insufficient available quantity or poor reliability (e.g., Supplier #4 *Tropical Imports Co* with reliability `0.50`), the agent calls `get_alternative_suppliers(product_id)`. It identifies alternative suppliers (e.g., Supplier #2 *BevCo Distribuidora*, reliability `0.92`, unit price `$2.80`) and returns an `INVESTIGATE` structured decision advising vendor reallocation.
- **Current Scope / Limitation:** Alternative supplier discovery and constraint checks operate during the **pre-order recommendation review phase**. The system does not currently feature an asynchronous event listener that takes an *already submitted, in-flight Purchase Order* and automatically splits it into multiple smaller POs across different suppliers.

---

### Scenario 3 — Demand / Forecast Has Changed (Deep Dive)
- **Implemented Behavior:** The agent dynamically computes net requirements by querying live `DemandForecast` records against on-hand `Inventory` and active `PurchaseOrder` quantities. If demand forecasts increase or decrease, any recommendation review triggered reflects the updated requirement.
- **Current Scope / Limitation:** Demand re-evaluation occurs when an AI review is triggered on a recommendation. The system does not currently include a background daemon/webhook that monitors POS sales spikes in real time to automatically revise existing, placed POs mid-cycle.

---

### Scenario 4 — Purchasing Constraints (Deep Dive)
- **Implemented Behavior:** The agent evaluates multiple hard business constraints simultaneously:
  - **Storage Constraint:** If warehouse capacity is limited (e.g., 150 units remaining), the agent scales the order down to fit storage limits.
  - **Budget Constraint:** If node budget is constrained (e.g., $1,000 available), the agent modifies or rejects the purchase to prevent budget overruns.
  - **MOQ Constraint:** If net demand is below supplier MOQ, the agent adjusts upward to meet MOQ or flags for human investigation.
- **Deterministic Enforcement:** All constraints are verified by backend code outside the LLM before committing transactions.

---

## 🛡️ Deterministic Validation Engine

```
       AI Proposes Purchase Action
                   │
                   ▼
┌──────────────────────────────────────┐
│    Deterministic Backend Validator   │  ◄── Evaluated strictly in Python/SQL
│    (Independent of LLM Reasoning)   │      Zero risk of hallucination
└──────────────────┬───────────────────┘
                   │
  ┌────────────────┼────────────────┬────────────────┬────────────────┬────────────────┐
  ▼                ▼                ▼                ▼                ▼                ▼
[Quantity > 0]  [MOQ Check]   [Budget Check]  [Storage Check]  [Supplier Stock] [PO Integrity]
  │                │                │                │                │                │
  └────────────────┴────────────────┴────────┬───────┴────────────────┴────────────────┘
                                             │
                                     ALL CHECKS PASS?
                                     ├── YES ──► Commit PO & Finalize
                                     └── NO  ──► Trigger Feedback Loop
```

The validation engine performs six distinct checks:

1. **Quantity Check:** Verifies order quantity is strictly greater than zero.
2. **MOQ Check:** Confirms order meets or exceeds `SupplierProduct.min_order_quantity`.
3. **Budget Check:** Validates that `quantity × unit_price` does not exceed node available budget.
4. **Storage Check:** Verifies that incoming stock + current stock does not exceed `FulfillmentNode.storage_capacity`.
5. **Supplier Availability Check:** Confirms supplier has sufficient physical stock to fulfill the order.
6. **PO Validity Check:** Verifies referential integrity (valid product, node, supplier, and currency).

---

## 🔁 Self-Correcting Feedback Loop

When a proposed purchase order fails deterministic validation, the failure is not simply dropped. The orchestrator feeds the exact validation error back to the Gemini chat session:

1. Agent receives error message (e.g., *"Storage check failed: Order of 500 units exceeds remaining capacity of 150"*).
2. Agent re-investigates constraints using tools.
3. Agent adjusts proposed quantity (e.g., modifying from 500 &rarr; 150 units).
4. Validation runs again.
5. The loop allows up to **3 correction iterations**. If constraints cannot be resolved, the recommendation is set to `REJECTED` or flagged for human review.

---

## 👤 Human Approval Gates

The agent automatically flags recommendations as `requires_human_approval = true` when any of the following risk thresholds are met:

- **Order Value:** Total cost exceeds **$10,000.00**
- **Order Volume:** Quantity exceeds **500 units**
- **Supplier Risk:** Supplier historical reliability score is below **0.80**
- **Quantity Delta:** Recommended quantity is modified by more than **30%** from the original suggestion

When flagged, the system transitions the recommendation to `PENDING_APPROVAL` and blocks execution until a buyer reviews the reasoning and clicks **Approve** or **Reject** in the UI.

---

## 📊 Database Schema & Seed Scenarios

The PostgreSQL database contains 9 relational tables:

```
Product ───────────────┬── SupplierProduct ── Supplier
                       ├── Inventory ──────── FulfillmentNode
                       ├── DemandForecast ─── FulfillmentNode
                       └── PurchasingRecommendation
                                │
                                ├── AgentDecision
                                ├── AgentActivityLog
                                └── PurchaseOrder ──── Budget
```

### Seed Recommendations:

| ID | Product | Node | Supplier | Recom Qty | Forecast | Stock | Open PO | Expected AI Outcome |
|---|---|---|---|---|---|---|---|---|
| **#1** | Organic Almonds 500g | Downtown Hub | NutriSource MX | 800 | 500 | 120 | 200 | **MODIFY &rarr; 180** (Net demand calculation) |
| **#2** | Cold Brew Coffee 330ml | Downtown Hub | BevCo Distribuidora | 200 | 280 | 80 | 0 | **ACCEPT &rarr; 200** (Normal replenishment) |
| **#3** | Protein Bar 60g | South Micro | NutriSource MX | 1500 | 100 | 50 | 0 | **REJECT** (Exceeds warehouse capacity & budget) |
| **#4** | Fresh Orange Juice 1L | Downtown Hub | FreshDirect LATAM | 300 | 350 | 50 | 0 | **ACCEPT &rarr; 300** (Meets MOQ & fits capacity) |
| **#5** | Coconut Water 500ml | Downtown Hub | Tropical Imports Co | 600 | 250 | 30 | 0 | **INVESTIGATE** (Low supplier reliability 0.50) |

---

## 🧪 Automated Testing

The test suite contains **32 passing tests** executing in under 2 seconds:

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Test Suite Coverage:
- **`test_agent.py` (8 tests):** Validates JSON decision parsing, code-block unwrapping, agent `ACCEPT`/`MODIFY`/`REJECT` decisions, human approval gating, and multi-iteration feedback loops.
- **`test_validation.py` (18 tests):** Unit tests for all 6 deterministic validation checks (budget limits, existing commitments, MOQ thresholds, storage overflow, supplier stock caps, zero quantity).
- **`test_demo.py` (6 tests):** Integration tests for demo scenario presets (`normal_replenishment`, `storage_constraint`, `supplier_constraint`, `budget_constraint`).

---

## 🚀 Local Setup & Installation

### Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- PostgreSQL 14+ (or Docker)

---

### 1. Clone the Repository
```bash
git clone https://github.com/anjali5674/ai-purchasing-agent.git
cd ai-purchasing-agent
```

---

### 2. Backend Setup
```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

Edit `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
DATABASE_URL=postgresql://purchasing_agent:purchasing_agent_dev@localhost:5432/purchasing_agent
LOG_LEVEL=INFO
```

---

### 3. Database Initialization & Seeding
Ensure PostgreSQL is running, create the database, and seed sample data:

```bash
# Optional: using Docker for PostgreSQL
docker-compose up -d

# Seed master catalog, inventory, forecasts, and recommendations
python -m app.database.seed
```

---

### 4. Run the Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```
Backend API will be live at: **[http://localhost:8000](http://localhost:8000)** (Interactive OpenAPI docs at `/docs`).

---

### 5. Frontend Setup
In a separate terminal:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Angular development server
npx ng serve --port 4200
```
Frontend UI will be live at: **[http://localhost:4200](http://localhost:4200)**.

---

## 🎯 Recommended Interview Demo Flow

To demonstrate the core system capabilities during an evaluation or interview:

1. **Dashboard Overview:** Open `http://localhost:4200`. Point out the active KPI summary cards, pending recommendations count, and fulfillment nodes.
2. **Review Recommendation #1 (Organic Almonds):** Navigate to `/recommendations/1`. Highlight that the initial suggestion is **800 units**.
3. **Run AI Review:** Click **"Run AI Review"**.
4. **Inspect Investigation Timeline:** Show the chronological sequence of Gemini tool calls (`get_product` &rarr; `get_inventory` &rarr; `get_demand_forecast` &rarr; `get_open_purchase_orders` &rarr; `get_storage_capacity` &rarr; `get_budget` &rarr; `get_supplier_details`).
5. **Highlight Net Requirement Reasoning:** Show the AI decision card:
   $$\text{Forecast (500)} - \text{Stock (120)} - \text{Open PO (200)} = \mathbf{180\text{ units}}$$
   Demonstrate that the agent reduced the order from 800 &rarr; 180 units and flagged human approval.
6. **Execute Human Approval:** Click **"Approve Purchase"**.
7. **Verify Deterministic Checks:** Show the resulting Purchase Order #4 creation and the green validation cards confirming all 6 checks passed.
8. **Demonstrate Constraint Handling:** Switch to Recommendation #3 (Protein Bar) or #5 (Coconut Water) to show how the agent rejects over-budget orders or investigates alternative suppliers when reliability is poor.

---

## 💡 Engineering Design Decisions

- **Why Native Gemini Function Calling instead of LangChain/CrewAI?** Direct tool calling using the official `google-genai` SDK provides deterministic control over tool dispatching, eliminates third-party abstractions, minimizes latency, and keeps memory footprints small.
- **Why Separate LLM Reasoning from Business Validation?** Large Language Models are probabilistic and prone to arithmetic hallucinations. Business constraints (budget balances, storage limits, legal supplier contracts) must be strictly enforced by deterministic Python/SQL code. The LLM *proposes* decisions; the backend *enforces* constraints.
- **Why Persistent PostgreSQL over In-Memory Mocking?** True purchasing workflows require relational integrity, transactional rollback, foreign keys, and persistent audit trails (`AgentActivityLog`).

---

## 🔮 Current Scope & Future Enhancements

- **Automated In-Flight PO Splitting:** The current implementation identifies alternative suppliers and checks supplier capacity during the *recommendation review* phase. A production extension would add an asynchronous webhook handler that listens for supplier shortage notices on *already submitted POs* and automatically generates split purchase orders.
- **Real-Time Demand Surge Ingestion:** Demand forecasting is currently queried dynamically from the database. A future iteration could integrate a Kafka/event stream to trigger proactive re-order investigations whenever point-of-sale velocity surges mid-week.

---

## 📄 License

This project is developed for technical evaluation purposes. All rights reserved.
