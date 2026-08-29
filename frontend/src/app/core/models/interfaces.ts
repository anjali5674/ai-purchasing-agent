/**
 * TypeScript interfaces matching the backend Pydantic schemas.
 * Provides type safety for API communication.
 */

// ---------------------------------------------------------------------------
// Product
// ---------------------------------------------------------------------------
export interface Product {
  id: number;
  sku: string;
  name: string;
  category: string;
  unit_price: number;
}

// ---------------------------------------------------------------------------
// Fulfillment Node
// ---------------------------------------------------------------------------
export interface FulfillmentNode {
  id: number;
  name: string;
  location: string;
  storage_capacity: number;
}

// ---------------------------------------------------------------------------
// Inventory
// ---------------------------------------------------------------------------
export interface Inventory {
  id: number;
  product_id: number;
  node_id: number;
  current_quantity: number;
  product?: Product;
  node?: FulfillmentNode;
}

// ---------------------------------------------------------------------------
// Supplier
// ---------------------------------------------------------------------------
export interface Supplier {
  id: number;
  name: string;
  lead_time_days: number;
  minimum_order_quantity: number;
  available_quantity: number;
  reliability_score: number;
}

// ---------------------------------------------------------------------------
// Purchase Order
// ---------------------------------------------------------------------------
export interface PurchaseOrder {
  id: number;
  product_id: number;
  supplier_id: number;
  node_id: number;
  quantity: number;
  unit_price: number;
  total_price: number;
  status: string;
  created_at: string;
  updated_at?: string;
  product?: Product;
  supplier?: Supplier;
  node?: FulfillmentNode;
}

// ---------------------------------------------------------------------------
// Agent Decision
// ---------------------------------------------------------------------------
export interface AgentDecision {
  id: number;
  recommendation_id: number;
  decision: 'ACCEPT' | 'MODIFY' | 'REJECT' | 'INVESTIGATE';
  suggested_quantity: number | null;
  reasoning: string;
  important_factors: string[];
  constraints_checked: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  requires_human_approval: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Agent Activity Log
// ---------------------------------------------------------------------------
export interface AgentActivityLog {
  id: number;
  recommendation_id: number;
  event_type: string;
  event_data: any;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Recommendation
// ---------------------------------------------------------------------------
export interface Recommendation {
  id: number;
  product_id: number;
  node_id: number;
  supplier_id?: number;
  recommended_quantity: number;
  status: string;
  created_at: string;
  product?: Product;
  node?: FulfillmentNode;
  decisions?: AgentDecision[];
  activity_logs?: AgentActivityLog[];
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------
export interface ValidationCheck {
  name: string;
  passed: boolean;
  message: string;
  actual_value?: number;
  limit_value?: number;
}

export interface ValidationResult {
  passed: boolean;
  checks: ValidationCheck[];
  purchase_order_id?: number;
}

// ---------------------------------------------------------------------------
// Agent Review Response
// ---------------------------------------------------------------------------
export interface AgentReviewResponse {
  recommendation_id: number;
  decision: AgentDecision;
  validation?: ValidationResult;
  purchase_order?: PurchaseOrder;
  feedback_iterations: number;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export interface DashboardSummary {
  pending_recommendations: number;
  pending_approvals: number;
  validation_failures: number;
  active_purchase_orders: number;
  recent_decisions: AgentDecision[];
}

// ---------------------------------------------------------------------------
// Recommendation Context (aggregated data for detail page)
// ---------------------------------------------------------------------------
export interface RecommendationContext {
  inventory: {
    current_quantity: number;
  };
  demand: {
    forecast_quantity: number;
    forecast_period: string | null;
  };
  open_purchase_orders: {
    count: number;
    total_quantity: number;
    orders: { id: number; quantity: number; status: string }[];
  };
  supplier: {
    id: number;
    name: string;
    lead_time_days: number;
    minimum_order_quantity: number;
    available_quantity: number;
    reliability_score: number;
    unit_price: number;
  } | null;
  budget: {
    total_budget: number;
    committed_spend: number;
    remaining: number;
  };
  storage: {
    total_capacity: number;
    current_usage: number;
    incoming: number;
    remaining: number;
  };
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  expected_behavior: string;
}

