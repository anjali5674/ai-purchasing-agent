import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ApiService } from '../../core/services/api.service';
import { Supplier } from '../../core/models/interfaces';

@Component({
  selector: 'app-supplier-list',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatTableModule, MatProgressSpinnerModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1>Suppliers</h1>
        <p>Registered suppliers and their capabilities</p>
      </div>

      <div *ngIf="loading" class="loading-container"><mat-spinner diameter="40"></mat-spinner></div>

      <mat-card *ngIf="!loading" class="fade-in-up" style="padding: 0 !important; overflow: hidden;">
        <table mat-table [dataSource]="suppliers">
          <ng-container matColumnDef="id">
            <th mat-header-cell *matHeaderCellDef>ID</th>
            <td mat-cell *matCellDef="let s">{{ s.id }}</td>
          </ng-container>
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let s" style="font-weight:500">{{ s.name }}</td>
          </ng-container>
          <ng-container matColumnDef="lead_time_days">
            <th mat-header-cell *matHeaderCellDef>Lead Time</th>
            <td mat-cell *matCellDef="let s">{{ s.lead_time_days }} days</td>
          </ng-container>
          <ng-container matColumnDef="minimum_order_quantity">
            <th mat-header-cell *matHeaderCellDef>MOQ</th>
            <td mat-cell *matCellDef="let s">{{ s.minimum_order_quantity | number }}</td>
          </ng-container>
          <ng-container matColumnDef="available_quantity">
            <th mat-header-cell *matHeaderCellDef>Available</th>
            <td mat-cell *matCellDef="let s">{{ s.available_quantity | number }}</td>
          </ng-container>
          <ng-container matColumnDef="reliability_score">
            <th mat-header-cell *matHeaderCellDef>Reliability</th>
            <td mat-cell *matCellDef="let s">
              <span [style.color]="s.reliability_score >= 0.8 ? 'var(--status-accept)' : s.reliability_score >= 0.6 ? 'var(--status-modify)' : 'var(--status-reject)'">
                {{ (s.reliability_score * 100) | number:'1.0-0' }}%
              </span>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns;"></tr>
        </table>
      </mat-card>
    </div>
  `,
})
export class SupplierListComponent implements OnInit {
  suppliers: Supplier[] = [];
  loading = true;
  columns = ['id', 'name', 'lead_time_days', 'minimum_order_quantity', 'available_quantity', 'reliability_score'];

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getSuppliers().subscribe({
      next: (data) => { this.suppliers = data; this.loading = false; },
      error: () => this.loading = false,
    });
  }
}
