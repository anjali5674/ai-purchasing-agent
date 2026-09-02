import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../core/services/api.service';
import { Recommendation } from '../../core/models/interfaces';

@Component({
  selector: 'app-recommendation-list',
  standalone: true,
  imports: [
    CommonModule, RouterLink,
    MatCardModule, MatTableModule, MatIconModule,
    MatButtonModule, MatProgressSpinnerModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>Purchase Recommendations</h1>
        <p>AI agent investigation and dual-supplier decision queue</p>
      </div>

      <div *ngIf="loading" class="loading-container">
        <mat-spinner diameter="40"></mat-spinner>
      </div>

      <mat-card *ngIf="!loading" class="fade-in-up" style="padding: 0 !important; overflow: hidden;">
        <table mat-table [dataSource]="recommendations" class="rec-table">
          <ng-container matColumnDef="id">
            <th mat-header-cell *matHeaderCellDef>ID</th>
            <td mat-cell *matCellDef="let r">
              <a [routerLink]="['/recommendations', r.id]" class="rec-link">#{{ r.id }}</a>
            </td>
          </ng-container>

          <ng-container matColumnDef="product">
            <th mat-header-cell *matHeaderCellDef>Product</th>
            <td mat-cell *matCellDef="let r">
              <div class="product-cell">
                <span class="product-name">{{ r.product?.name || 'Product ' + r.product_id }}</span>
                <span class="product-sku">{{ r.product?.sku }}</span>
              </div>
            </td>
          </ng-container>

          <ng-container matColumnDef="node">
            <th mat-header-cell *matHeaderCellDef>Fulfillment Node</th>
            <td mat-cell *matCellDef="let r">{{ r.node?.name || 'Node ' + r.node_id }}</td>
          </ng-container>

          <ng-container matColumnDef="suppliers">
            <th mat-header-cell *matHeaderCellDef>Candidate Suppliers</th>
            <td mat-cell *matCellDef="let r">
              <div class="suppliers-cell">
                <span class="sup-chip primary" *ngIf="r.primary_supplier">
                  <mat-icon>local_shipping</mat-icon> {{ r.primary_supplier.name }}
                </span>
                <span class="sup-chip secondary" *ngIf="r.secondary_supplier">
                  <mat-icon>alt_route</mat-icon> {{ r.secondary_supplier.name }}
                </span>
                <span *ngIf="!r.primary_supplier && !r.secondary_supplier" class="text-muted">None</span>
              </div>
            </td>
          </ng-container>

          <ng-container matColumnDef="quantity">
            <th mat-header-cell *matHeaderCellDef>Recommended Qty</th>
            <td mat-cell *matCellDef="let r">
              <span class="qty">{{ r.recommended_quantity | number }}</span>
            </td>
          </ng-container>

          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let r">
              <span class="status-badge" [ngClass]="r.status.toLowerCase()">
                {{ r.status.replace('_', ' ') }}
              </span>
            </td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let r">
              <button mat-icon-button [routerLink]="['/recommendations', r.id]">
                <mat-icon>arrow_forward</mat-icon>
              </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="clickable-row"></tr>
        </table>
      </mat-card>
    </div>
  `,
  styles: [`
    .rec-table {
      width: 100%;
    }

    .rec-link {
      color: var(--accent-cyan);
      text-decoration: none;
      font-weight: 600;
      &:hover { text-decoration: underline; }
    }

    .product-cell {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .product-name {
      font-weight: 500;
    }

    .product-sku {
      font-size: 12px;
      color: var(--text-muted);
      font-family: monospace;
    }

    .suppliers-cell {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sup-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      width: fit-content;
      mat-icon { font-size: 13px; width: 13px; height: 13px; }
      &.primary {
        background: rgba(6, 182, 212, 0.12);
        color: var(--accent-cyan);
      }
      &.secondary {
        background: rgba(255, 255, 255, 0.06);
        color: var(--text-secondary);
      }
    }

    .text-muted {
      font-size: 12px;
      color: var(--text-muted);
    }

    .qty {
      font-weight: 600;
      font-size: 15px;
    }

    .clickable-row {
      cursor: pointer;
      transition: background 0.15s;
      &:hover { background: rgba(255, 255, 255, 0.03); }
    }
  `],
})
export class RecommendationListComponent implements OnInit {
  recommendations: Recommendation[] = [];
  loading = true;
  displayedColumns = ['id', 'product', 'node', 'suppliers', 'quantity', 'status', 'actions'];

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getRecommendations().subscribe({
      next: (data) => {
        this.recommendations = data;
        this.loading = false;
      },
      error: () => this.loading = false,
    });
  }
}
