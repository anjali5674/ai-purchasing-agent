import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Product, Recommendation, AgentReviewResponse,
  AgentActivityLog, PurchaseOrder, Supplier,
  Inventory, DashboardSummary, ValidationResult,
  RecommendationContext,
} from '../models/interfaces';

const API = 'http://localhost:8000/api';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  // Products
  getProducts(): Observable<Product[]> {
    return this.http.get<Product[]>(`${API}/products`);
  }

  getProduct(id: number): Observable<Product> {
    return this.http.get<Product>(`${API}/products/${id}`);
  }

  // Recommendations
  getRecommendations(): Observable<Recommendation[]> {
    return this.http.get<Recommendation[]>(`${API}/recommendations`);
  }

  getRecommendation(id: number): Observable<Recommendation> {
    return this.http.get<Recommendation>(`${API}/recommendations/${id}`);
  }

  approveRecommendation(id: number): Observable<any> {
    return this.http.post(`${API}/recommendations/${id}/approve`, {});
  }

  rejectRecommendation(id: number): Observable<any> {
    return this.http.post(`${API}/recommendations/${id}/reject`, {});
  }

  getRecommendationContext(id: number): Observable<RecommendationContext> {
    return this.http.get<RecommendationContext>(`${API}/recommendations/${id}/context`);
  }

  // Agent
  triggerAgentReview(recommendationId: number, context?: string): Observable<AgentReviewResponse> {
    return this.http.post<AgentReviewResponse>(
      `${API}/agent/review/${recommendationId}`,
      context ? { context } : {}
    );
  }

  getAgentActivity(recommendationId: number): Observable<AgentActivityLog[]> {
    return this.http.get<AgentActivityLog[]>(`${API}/agent/activity/${recommendationId}`);
  }

  // Purchase Orders
  getPurchaseOrders(): Observable<PurchaseOrder[]> {
    return this.http.get<PurchaseOrder[]>(`${API}/purchase-orders`);
  }

  validatePurchaseOrder(orderId: number): Observable<ValidationResult> {
    return this.http.post<ValidationResult>(`${API}/purchase-orders/${orderId}/validate`, {});
  }

  // Suppliers
  getSuppliers(): Observable<Supplier[]> {
    return this.http.get<Supplier[]>(`${API}/suppliers`);
  }

  // Inventory
  getInventory(productId?: number, nodeId?: number): Observable<Inventory[]> {
    let params: any = {};
    if (productId) params.product_id = productId;
    if (nodeId) params.node_id = nodeId;
    return this.http.get<Inventory[]>(`${API}/inventory`, { params });
  }

  // Dashboard
  getDashboardSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${API}/dashboard/summary`);
  }

  // Demo Scenarios
  getDemoScenarios(): Observable<any[]> {
    return this.http.get<any[]>(`${API}/demo/scenarios`);
  }

  applyDemoScenario(scenarioId: string): Observable<any> {
    return this.http.post<any>(`${API}/demo/scenarios/${scenarioId}`, {});
  }
}
