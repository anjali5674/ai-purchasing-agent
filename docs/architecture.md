# Architecture Document — AI Purchasing Agent

## Overview

This document describes the architecture of the AI Purchasing Agent system. The system is designed to demonstrate an AI agent that can make, execute, and validate purchasing decisions — not a chatbot.

## System Components

### 1. Angular Frontend
- **Role**: Presentation layer only
- **No business logic** — all decisions happen server-side
- **Angular Material** for enterprise-grade UI components
- **Lazy-loaded** feature modules for performance
- Communicates with backend via REST API

### 2. FastAPI Backend
- **Single application server** — no microservices
- **API layer**: Route handlers with Pydantic validation
- **Agent orchestrator**: Manages the Google Gemini tool-calling loop
- **Validation engine**: Deterministic business rule checks
- **Database access**: SQLAlchemy ORM

### 3. AI Agent (Orchestrator + Google Gemini)
- Uses **Google Gemini API** (`google-genai` SDK) with native function calling
- The agent chooses which tools to call based on the recommendation context
- Tool calls are executed server-side, results fed back to the LLM
- Final decision is structured JSON (parsed and validated)
- Maximum 10 tool-calling rounds as a safety limit

### 4. Validation Engine
- **Completely independent from the LLM**
- Pure Python functions that check business rules
- Runs after PO creation/modification
- Returns individual PASS/FAIL for each constraint
- Powers the feedback loop (failures → agent re-investigation)

### 5. PostgreSQL Database
- Single database, clean relational schema
- No migrations (tables created via `Base.metadata.create_all`)
- Appropriate for interview scope — Alembic would be added for production

## Key Architectural Patterns

### Tool-Calling Loop
```
System prompt + User message + Tool definitions
         → Google Gemini
         ← function_calls response
         → Execute tools locally, return function responses
         → Google Gemini (with tool results)
         ← Final decision JSON (or more function_calls)
         → Parse and store
```

### Validation Feedback Loop
```
Agent Decision → Create PO → Validate
                                ↓
                          PASS → Finalize PO
                          FAIL → Feed failure to agent
                               → Agent re-investigates
                               → Corrected recommendation
                               → Validate again
                               → (max 3 iterations)
```

### Human Approval Gate
The agent sets `requires_human_approval: true` when:
- Order value > $10,000
- Quantity > 500 units
- Supplier reliability < 0.8
- Significant quantity change (>30%)

When flagged, the recommendation status becomes `PENDING_APPROVAL`. The PO is NOT created until the buyer explicitly approves.

## Data Flow

1. **Frontend** sends `POST /api/agent/review/{id}`
2. **Backend** loads the recommendation, sets status to `UNDER_REVIEW`
3. **Orchestrator** builds context message, sends to Google Gemini with tool definitions
4. **Google Gemini** returns tool calls → tools execute → results sent back
5. **Google Gemini** returns final structured decision JSON
6. **Backend** stores the AgentDecision and AgentActivityLog entries
7. If ACCEPT/MODIFY and no approval needed:
   - Create PO → Run validation → Feedback loop if needed
8. If approval needed:
   - Set status to PENDING_APPROVAL, return to frontend
9. **Frontend** displays the full investigation timeline, decision, and validation

## Security Considerations

- API keys stored in `.env`, never in source code
- `.env` is in `.gitignore`
- The LLM cannot execute arbitrary SQL — all DB access goes through predefined tools
- Tool functions use parameterized SQLAlchemy queries
- CORS restricted to Angular dev server origin

## Scalability Notes (for interview discussion)

For production, these additions would be relevant:
- **Task queue (Celery/Temporal)** for long-running agent investigations
- **WebSocket/SSE** for streaming agent activity to the UI
- **Alembic** for schema migrations
- **Caching layer** for frequently-accessed product/supplier data
