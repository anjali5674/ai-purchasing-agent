import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../core/services/api.service';
import { PurchaseOrder } from '../../core/models/interfaces';

@Component({
  selector: 'app-purchase-order-list',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatTableModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>Purchase Orders</h1>
        <p>All purchase orders across fulfillment nodes</p>
      </div>

      <div *ngIf="loading" class="loading-container"><mat-spinner diameter="40"></mat-spinner></div>

      <mat-card *ngIf="!loading" class="fade-in-up" style="padding: 0 !important; overflow: hidden;">
        <table mat-table [dataSource]="orders">
          <ng-container matColumnDef="id">
            <th mat-header-cell *matHeaderCellDef>PO #</th>
            <td mat-cell *matCellDef="let o">#{{ o.id }}</td>
          </ng-container>
          <ng-container matColumnDef="product">
            <th mat-header-cell *matHeaderCellDef>Product</th>
            <td mat-cell *matCellDef="let o">{{ o.product?.name || 'Product ' + o.product_id }}</td>
          </ng-container>
          <ng-container matColumnDef="supplier">
            <th mat-header-cell *matHeaderCellDef>Supplier</th>
            <td mat-cell *matCellDef="let o">{{ o.supplier?.name || 'Supplier ' + o.supplier_id }}</td>
          </ng-container>
          <ng-container matColumnDef="quantity">
            <th mat-header-cell *matHeaderCellDef>Quantity</th>
            <td mat-cell *matCellDef="let o">{{ o.quantity | number }}</td>
          </ng-container>
          <ng-container matColumnDef="total_price">
            <th mat-header-cell *matHeaderCellDef>Total</th>
            <td mat-cell *matCellDef="let o">\${{ o.total_price | number:'1.2-2' }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let o">
              <span class="status-badge" [ngClass]="o.status.toLowerCase()">{{ o.status }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="created_at">
            <th mat-header-cell *matHeaderCellDef>Created</th>
            <td mat-cell *matCellDef="let o">{{ o.created_at | date:'shortDate' }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns;"></tr>
        </table>
      </mat-card>
    </div>
  `,
})
export class PurchaseOrderListComponent implements OnInit {
  orders: PurchaseOrder[] = [];
  loading = true;
  columns = ['id', 'product', 'supplier', 'quantity', 'total_price', 'status', 'created_at'];

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getPurchaseOrders().subscribe({
      next: (data) => { this.orders = data; this.loading = false; },
      error: () => this.loading = false,
    });
  }
}
