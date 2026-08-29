import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../core/services/api.service';
import { Inventory } from '../../core/models/interfaces';

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatTableModule, MatProgressSpinnerModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>Inventory</h1>
        <p>Current stock levels across all fulfillment nodes</p>
      </div>

      <div *ngIf="loading" class="loading-container"><mat-spinner diameter="40"></mat-spinner></div>

      <mat-card *ngIf="!loading" class="fade-in-up" style="padding: 0 !important; overflow: hidden;">
        <table mat-table [dataSource]="inventory">
          <ng-container matColumnDef="product">
            <th mat-header-cell *matHeaderCellDef>Product</th>
            <td mat-cell *matCellDef="let i">
              <div>
                <div style="font-weight:500">{{ i.product?.name || 'Product ' + i.product_id }}</div>
                <div style="font-size:12px; color:var(--text-muted); font-family:monospace">{{ i.product?.sku }}</div>
              </div>
            </td>
          </ng-container>
          <ng-container matColumnDef="node">
            <th mat-header-cell *matHeaderCellDef>Fulfillment Node</th>
            <td mat-cell *matCellDef="let i">{{ i.node?.name || 'Node ' + i.node_id }}</td>
          </ng-container>
          <ng-container matColumnDef="current_quantity">
            <th mat-header-cell *matHeaderCellDef>Current Quantity</th>
            <td mat-cell *matCellDef="let i" style="font-weight:600; font-size:15px">
              {{ i.current_quantity | number }}
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns;"></tr>
        </table>
      </mat-card>
    </div>
  `,
})
export class InventoryComponent implements OnInit {
  inventory: Inventory[] = [];
  loading = true;
  columns = ['product', 'node', 'current_quantity'];

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getInventory().subscribe({
      next: (data) => { this.inventory = data; this.loading = false; },
      error: () => this.loading = false,
    });
  }
}
