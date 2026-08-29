import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet, RouterLink, RouterLinkActive,
    MatToolbarModule, MatSidenavModule, MatListModule,
    MatIconModule, MatButtonModule,
  ],
  template: `
    <mat-sidenav-container class="app-container">
      <mat-sidenav mode="side" opened class="app-sidenav">
        <div class="sidenav-header">
          <mat-icon class="logo-icon">smart_toy</mat-icon>
          <div class="logo-text">
            <span class="logo-title">AI Purchasing</span>
            <span class="logo-subtitle">Agent System</span>
          </div>
        </div>

        <mat-nav-list>
          <a mat-list-item routerLink="/dashboard" routerLinkActive="active-link">
            <mat-icon matListItemIcon>dashboard</mat-icon>
            <span matListItemTitle>Dashboard</span>
          </a>
          <a mat-list-item routerLink="/recommendations" routerLinkActive="active-link">
            <mat-icon matListItemIcon>recommend</mat-icon>
            <span matListItemTitle>Recommendations</span>
          </a>
          <a mat-list-item routerLink="/purchase-orders" routerLinkActive="active-link">
            <mat-icon matListItemIcon>receipt_long</mat-icon>
            <span matListItemTitle>Purchase Orders</span>
          </a>
          <a mat-list-item routerLink="/suppliers" routerLinkActive="active-link">
            <mat-icon matListItemIcon>local_shipping</mat-icon>
            <span matListItemTitle>Suppliers</span>
          </a>
          <a mat-list-item routerLink="/inventory" routerLinkActive="active-link">
            <mat-icon matListItemIcon>inventory_2</mat-icon>
            <span matListItemTitle>Inventory</span>
          </a>
        </mat-nav-list>
      </mat-sidenav>

      <mat-sidenav-content class="app-content">
        <router-outlet></router-outlet>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .app-container {
      height: 100vh;
    }

    .app-sidenav {
      width: 260px;
      background: var(--bg-secondary);
      border-right: 1px solid var(--border-color);
    }

    .sidenav-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 24px 20px;
      border-bottom: 1px solid var(--border-color);
    }

    .logo-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: var(--accent-cyan);
    }

    .logo-text {
      display: flex;
      flex-direction: column;
    }

    .logo-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .logo-subtitle {
      font-size: 11px;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .app-content {
      background: var(--bg-primary);
    }

    .active-link {
      background: rgba(34, 211, 238, 0.08) !important;
      border-right: 3px solid var(--accent-cyan);
    }

    .active-link mat-icon {
      color: var(--accent-cyan) !important;
    }
  `],
})
export class AppComponent {}
