import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { DashboardSummary, Recommendation } from '../../core/models/interfaces';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule, RouterLink,
    MatCardModule, MatIconModule, MatTableModule,
    MatButtonModule, MatChipsModule, MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>Purchasing Dashboard</h1>
        <p>AI-powered purchasing decision support system</p>
      </div>

      <div *ngIf="loading" class="loading-container">
        <mat-spinner diameter="40"></mat-spinner>
      </div>

      <div *ngIf="!loading" class="dashboard-content fade-in-up">
        <!-- Stat Cards -->
        <div class="stat-grid">
          <mat-card class="stat-card" [routerLink]="['/recommendations']">
            <div class="stat-icon products-icon">
              <mat-icon>inventory_2</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ totalProducts }}</span>
              <span class="stat-label">Total Products</span>
            </div>
          </mat-card>

          <mat-card class="stat-card" [routerLink]="['/recommendations']">
            <div class="stat-icon pending-icon">
              <mat-icon>pending_actions</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ summary?.pending_recommendations || 0 }}</span>
              <span class="stat-label">Pending Recommendations</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon approval-icon">
              <mat-icon>how_to_reg</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ summary?.pending_approvals || 0 }}</span>
              <span class="stat-label">Pending Approvals</span>
            </div>
          </mat-card>

          <mat-card class="stat-card" [routerLink]="['/purchase-orders']">
            <div class="stat-icon active-icon">
              <mat-icon>receipt_long</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ summary?.active_purchase_orders || 0 }}</span>
              <span class="stat-label">Active Purchase Orders</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon failure-icon">
              <mat-icon>error_outline</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ summary?.validation_failures || 0 }}</span>
              <span class="stat-label">Validation Failures</span>
            </div>
          </mat-card>
        </div>

        <!-- Purchasing Recommendations Table -->
        <mat-card class="table-card">
          <div class="card-header">
            <h2>
              <mat-icon>recommend</mat-icon>
              Purchasing Recommendations
            </h2>
            <button mat-stroked-button routerLink="/recommendations">View All</button>
          </div>

          <div class="table-container">
            <table mat-table [dataSource]="recommendations" *ngIf="recommendations.length > 0">
              <ng-container matColumnDef="product">
                <th mat-header-cell *matHeaderCellDef>Product</th>
                <td mat-cell *matCellDef="let r">
                  <div class="product-cell">
                    <span class="product-name">{{ r.product?.name }}</span>
                  </div>
                </td>
              </ng-container>

              <ng-container matColumnDef="sku">
                <th mat-header-cell *matHeaderCellDef>SKU</th>
                <td mat-cell *matCellDef="let r">
                  <span class="mono">{{ r.product?.sku }}</span>
                </td>
              </ng-container>

              <ng-container matColumnDef="node">
                <th mat-header-cell *matHeaderCellDef>Fulfillment Node</th>
                <td mat-cell *matCellDef="let r">{{ r.node?.name }}</td>
              </ng-container>

              <ng-container matColumnDef="quantity">
                <th mat-header-cell *matHeaderCellDef>Recommended Qty</th>
                <td mat-cell *matCellDef="let r">
                  <span class="qty-value">{{ r.recommended_quantity | number }}</span>
                </td>
              </ng-container>

              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let r">
                  <span class="status-badge" [ngClass]="r.status.toLowerCase()">
                    {{ formatStatus(r.status) }}
                  </span>
                </td>
              </ng-container>

              <ng-container matColumnDef="decision">
                <th mat-header-cell *matHeaderCellDef>AI Decision</th>
                <td mat-cell *matCellDef="let r">
                  <span *ngIf="r.decisions?.length" class="status-badge"
                        [ngClass]="r.decisions[r.decisions.length - 1].decision.toLowerCase()">
                    {{ r.decisions[r.decisions.length - 1].decision }}
                  </span>
                  <span *ngIf="!r.decisions?.length" class="no-decision">—</span>
                </td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Action</th>
                <td mat-cell *matCellDef="let r">
                  <button mat-stroked-button color="primary"
                          [routerLink]="['/recommendations', r.id]"
                          class="review-btn">
                    <mat-icon>arrow_forward</mat-icon>
                    {{ r.status === 'PENDING' ? 'Review' : 'View' }}
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="recColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: recColumns;" class="clickable-row"
                  [routerLink]="['/recommendations', row.id]"></tr>
            </table>

            <div *ngIf="recommendations.length === 0" class="empty-state">
              <mat-icon>smart_toy</mat-icon>
              <p>No recommendations yet. Seed the database to get started.</p>
            </div>
          </div>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .stat-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-card {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 20px !important;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
      &:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
      }
    }

    .stat-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      mat-icon { font-size: 22px; width: 22px; height: 22px; }
    }

    .products-icon { background: rgba(167, 139, 250, 0.12); mat-icon { color: #a78bfa; } }
    .pending-icon { background: rgba(251, 191, 36, 0.12); mat-icon { color: #fbbf24; } }
    .approval-icon { background: rgba(96, 165, 250, 0.12); mat-icon { color: #60a5fa; } }
    .active-icon { background: rgba(34, 211, 238, 0.12); mat-icon { color: #22d3ee; } }
    .failure-icon { background: rgba(248, 113, 113, 0.12); mat-icon { color: #f87171; } }

    .stat-info { display: flex; flex-direction: column; }

    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: 11px;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .table-card { padding: 0 !important; overflow: hidden; }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      h2 {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 16px;
        font-weight: 600;
        mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--accent-cyan); }
      }
    }

    .table-container { overflow-x: auto; }

    table { width: 100%; }

    .product-cell { display: flex; flex-direction: column; gap: 2px; }
    .product-name { font-weight: 500; }
    .mono { font-family: 'JetBrains Mono', 'SF Mono', monospace; font-size: 12px; color: var(--text-secondary); }
    .qty-value { font-weight: 600; font-size: 15px; }
    .no-decision { color: var(--text-muted); }

    .review-btn {
      mat-icon { font-size: 16px; width: 16px; height: 16px; margin-right: 4px; }
    }

    .clickable-row {
      cursor: pointer;
      transition: background 0.15s;
      &:hover { background: rgba(255, 255, 255, 0.03); }
    }

    .empty-state {
      text-align: center;
      padding: 48px;
      color: var(--text-secondary);
      mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 12px; opacity: 0.4; }
    }

    @media (max-width: 1400px) {
      .stat-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 800px) {
      .stat-grid { grid-template-columns: repeat(2, 1fr); }
    }
  `],
})
export class DashboardComponent implements OnInit {
  summary: DashboardSummary | null = null;
  recommendations: Recommendation[] = [];
  totalProducts = 0;
  loading = true;
  recColumns = ['product', 'sku', 'node', 'quantity', 'status', 'decision', 'actions'];

  constructor(private api: ApiService) {}

  ngOnInit() {
    forkJoin({
      summary: this.api.getDashboardSummary(),
      recommendations: this.api.getRecommendations(),
      products: this.api.getProducts(),
    }).subscribe({
      next: ({ summary, recommendations, products }) => {
        this.summary = summary;
        this.recommendations = recommendations;
        this.totalProducts = products.length;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  formatStatus(status: string): string {
    return status.replace(/_/g, ' ');
  }
}
