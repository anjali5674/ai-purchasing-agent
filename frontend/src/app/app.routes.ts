import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'recommendations',
    loadComponent: () => import('./features/recommendations/recommendation-list.component').then(m => m.RecommendationListComponent),
  },
  {
    path: 'recommendations/:id',
    loadComponent: () => import('./features/recommendations/recommendation-detail.component').then(m => m.RecommendationDetailComponent),
  },
  {
    path: 'purchase-orders',
    loadComponent: () => import('./features/purchase-orders/purchase-order-list.component').then(m => m.PurchaseOrderListComponent),
  },
  {
    path: 'suppliers',
    loadComponent: () => import('./features/suppliers/supplier-list.component').then(m => m.SupplierListComponent),
  },
  {
    path: 'inventory',
    loadComponent: () => import('./features/inventory/inventory.component').then(m => m.InventoryComponent),
  },
];
