import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import {
  Recommendation, AgentDecision, AgentActivityLog,
  AgentReviewResponse, ValidationResult, RecommendationContext,
} from '../../core/models/interfaces';

@Component({
  selector: 'app-recommendation-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule, MatIconModule, MatButtonModule,
    MatDividerModule, MatProgressSpinnerModule,
    MatProgressBarModule, MatSnackBarModule, MatDialogModule,
  ],
  template: `
    <div class="page-container">
      <div *ngIf="loading" class="loading-container">
        <mat-spinner diameter="40"></mat-spinner>
      </div>

      <div *ngIf="!loading && recommendation" class="detail-content fade-in-up">
        <!-- Header -->
        <div class="detail-header">
          <div class="header-left">
            <h1>Recommendation #{{ recommendation.id }}</h1>
            <span class="status-badge" [ngClass]="recommendation.status.toLowerCase()">
              {{ formatStatus(recommendation.status) }}
            </span>
          </div>
          <div class="header-actions">
            <button mat-raised-button color="primary"
                    (click)="triggerReview()"
                    [disabled]="reviewing"
                    *ngIf="recommendation.status !== 'APPROVED'">
              <mat-icon>{{ recommendation.status === 'PENDING' ? 'smart_toy' : 'refresh' }}</mat-icon>
              {{ recommendation.status === 'PENDING' ? 'Run AI Review' : 'Re-run AI Review' }}
            </button>
          </div>
        </div>

        <!-- Demo Scenarios Bar -->
        <mat-card class="scenario-card">
          <div class="scenario-header">
            <div class="scenario-title">
              <mat-icon>tune</mat-icon>
              <span>Live Database Demo Scenarios</span>
            </div>
            <span class="scenario-subtitle">Modify real PostgreSQL constraints to test agent reasoning:</span>
          </div>
          <div class="scenario-buttons">
            <button mat-stroked-button (click)="loadScenario('normal_replenishment')" [disabled]="loading || reviewing"
                    [class.active-scenario]="activeScenario === 'normal_replenishment'">
              <mat-icon>check_circle</mat-icon> A: Normal
            </button>
            <button mat-stroked-button (click)="loadScenario('storage_constraint')" [disabled]="loading || reviewing"
                    [class.active-scenario]="activeScenario === 'storage_constraint'">
              <mat-icon>warehouse</mat-icon> B: Storage Limit
            </button>
            <button mat-stroked-button (click)="loadScenario('supplier_constraint')" [disabled]="loading || reviewing"
                    [class.active-scenario]="activeScenario === 'supplier_constraint'">
              <mat-icon>local_shipping</mat-icon> C: Supplier Stock Low
            </button>
            <button mat-stroked-button (click)="loadScenario('budget_constraint')" [disabled]="loading || reviewing"
                    [class.active-scenario]="activeScenario === 'budget_constraint'">
              <mat-icon>account_balance_wallet</mat-icon> D: Budget Limit
            </button>
          </div>
        </mat-card>

        <!-- Review Progress -->
        <mat-progress-bar *ngIf="reviewing" mode="indeterminate" color="primary"
                          class="review-progress"></mat-progress-bar>

        <!-- ============================================================ -->
        <!-- SECTION 1: Product + Inventory + Supplier + Constraints Grid -->
        <!-- ============================================================ -->
        <div class="context-grid">
          <!-- Product Information -->
          <mat-card class="info-card">
            <h3><mat-icon>category</mat-icon> Product Information</h3>
            <div class="info-row">
              <span class="info-label">Product</span>
              <span class="info-value">{{ recommendation.product?.name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">SKU</span>
              <span class="info-value mono">{{ recommendation.product?.sku }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Category</span>
              <span class="info-value">{{ recommendation.product?.category }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Unit Price</span>
              <span class="info-value">\${{ recommendation.product?.unit_price | number:'1.2-2' }}</span>
            </div>
          </mat-card>

          <!-- Inventory & Demand -->
          <mat-card class="info-card">
            <h3><mat-icon>warehouse</mat-icon> Inventory & Demand</h3>
            <div class="info-row">
              <span class="info-label">Current Inventory</span>
              <span class="info-value highlight">{{ context?.inventory?.current_quantity | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Expected Demand</span>
              <span class="info-value">{{ context?.demand?.forecast_quantity | number }}</span>
            </div>
            <div class="info-row" *ngIf="context?.demand?.forecast_period">
              <span class="info-label">Forecast Period</span>
              <span class="info-value">{{ context?.demand?.forecast_period }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Open Purchase Orders</span>
              <span class="info-value">
                {{ context?.open_purchase_orders?.count || 0 }} orders
                ({{ context?.open_purchase_orders?.total_quantity | number }} units incoming)
              </span>
            </div>
          </mat-card>

          <!-- Supplier -->
          <mat-card class="info-card" *ngIf="context?.supplier">
            <h3><mat-icon>local_shipping</mat-icon> Supplier</h3>
            <div class="info-row">
              <span class="info-label">Supplier</span>
              <span class="info-value">{{ context?.supplier?.name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Lead Time</span>
              <span class="info-value">{{ context?.supplier?.lead_time_days }} days</span>
            </div>
            <div class="info-row">
              <span class="info-label">MOQ</span>
              <span class="info-value">{{ context?.supplier?.minimum_order_quantity | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Available Quantity</span>
              <span class="info-value">{{ context?.supplier?.available_quantity | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Reliability</span>
              <span class="info-value"
                    [style.color]="(context?.supplier?.reliability_score || 0) >= 0.8 ? 'var(--status-accept)' : 'var(--status-modify)'">
                {{ ((context?.supplier?.reliability_score || 0) * 100) | number:'1.0-0' }}%
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">Supplier Price</span>
              <span class="info-value">\${{ context?.supplier?.unit_price | number:'1.2-2' }}</span>
            </div>
          </mat-card>

          <!-- Constraints -->
          <mat-card class="info-card">
            <h3><mat-icon>rule</mat-icon> Constraints</h3>
            <div class="info-row">
              <span class="info-label">Budget (Total)</span>
              <span class="info-value">\${{ context?.budget?.total_budget | number:'1.0-0' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Budget (Committed)</span>
              <span class="info-value">\${{ context?.budget?.committed_spend | number:'1.2-2' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Budget (Remaining)</span>
              <span class="info-value highlight">\${{ context?.budget?.remaining | number:'1.2-2' }}</span>
            </div>
            <mat-divider></mat-divider>
            <div class="info-row">
              <span class="info-label">Storage Capacity</span>
              <span class="info-value">{{ context?.storage?.total_capacity | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Storage Used</span>
              <span class="info-value">{{ context?.storage?.current_usage | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Storage Incoming</span>
              <span class="info-value">{{ context?.storage?.incoming | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Storage Remaining</span>
              <span class="info-value highlight"
                    [style.color]="(context?.storage?.remaining || 0) < (recommendation.recommended_quantity || 0) ? 'var(--status-reject)' : 'var(--status-accept)'">
                {{ context?.storage?.remaining | number }}
              </span>
            </div>
          </mat-card>
        </div>

        <!-- ============================================================ -->
        <!-- SECTION 2: Recommendation Summary -->
        <!-- ============================================================ -->
        <mat-card class="section-card recommendation-summary" *ngIf="latestDecision">
          <h3><mat-icon>psychology</mat-icon> AI Decision</h3>

          <div class="decision-row">
            <div class="decision-item">
              <span class="decision-label">Original Quantity</span>
              <span class="decision-value">{{ recommendation.recommended_quantity | number }}</span>
            </div>
            <div class="decision-item" *ngIf="latestDecision.suggested_quantity">
              <span class="decision-label">AI Suggested Quantity</span>
              <span class="decision-value accent">{{ latestDecision.suggested_quantity | number }}</span>
            </div>
            <div class="decision-item">
              <span class="decision-label">Decision</span>
              <span class="decision-badge" [ngClass]="latestDecision.decision.toLowerCase()">
                {{ latestDecision.decision }}
              </span>
            </div>
            <div class="decision-item">
              <span class="decision-label">Confidence</span>
              <span class="confidence-badge" [ngClass]="latestDecision.confidence.toLowerCase()">
                {{ latestDecision.confidence }}
              </span>
            </div>
            <div class="decision-item">
              <span class="decision-label">Human Approval</span>
              <span [ngClass]="latestDecision.requires_human_approval ? 'required' : 'not-required'">
                {{ latestDecision.requires_human_approval ? 'Required' : 'Not Required' }}
              </span>
            </div>
          </div>

          <!-- Reasoning -->
          <div class="reasoning-section">
            <h4>Reasoning</h4>
            <p>{{ latestDecision.reasoning }}</p>
          </div>

          <!-- Important Factors -->
          <div *ngIf="latestDecision.important_factors?.length" class="factors-section">
            <h4>Important Factors</h4>
            <ul>
              <li *ngFor="let factor of latestDecision.important_factors">{{ factor }}</li>
            </ul>
          </div>

          <!-- Constraints Checked -->
          <div *ngIf="latestDecision.constraints_checked?.length" class="constraints-section">
            <h4>Constraints Checked</h4>
            <div class="constraint-chips">
              <span *ngFor="let c of latestDecision.constraints_checked" class="constraint-chip">
                <mat-icon class="check-pass">check_circle</mat-icon>
                {{ c }}
              </span>
            </div>
          </div>

          <!-- Human Approval Actions -->
          <div *ngIf="latestDecision.requires_human_approval && recommendation.status === 'PENDING_APPROVAL'"
               class="approval-section">
            <mat-divider></mat-divider>
            <h4><mat-icon>verified_user</mat-icon> Human Approval Required</h4>
            <p class="approval-message">This purchasing action requires buyer approval before execution.</p>
            <div class="approval-actions">
              <button mat-raised-button color="primary" (click)="confirmApprove()" [disabled]="acting">
                <mat-icon>check</mat-icon> Approve Purchase
              </button>
              <button mat-raised-button color="warn" (click)="confirmReject()" [disabled]="acting">
                <mat-icon>close</mat-icon> Reject
              </button>
              <button mat-stroked-button (click)="triggerReview()" [disabled]="acting">
                <mat-icon>refresh</mat-icon> Re-investigate
              </button>
            </div>
          </div>
        </mat-card>

        <!-- ============================================================ -->
        <!-- SECTION 3: Agent Investigation Timeline -->
        <!-- ============================================================ -->
        <mat-card *ngIf="activityLogs.length > 0" class="section-card">
          <h3><mat-icon>timeline</mat-icon> Agent Investigation Timeline</h3>
          <div class="timeline">
            <div *ngFor="let log of activityLogs; let i = index" class="timeline-item"
                 [ngClass]="getTimelineClass(log.event_type)">
              <div class="timeline-dot">
                <mat-icon>{{ getEventIcon(log.event_type) }}</mat-icon>
              </div>
              <div class="timeline-connector" *ngIf="i < activityLogs.length - 1"></div>
              <div class="timeline-content">
                <div class="timeline-header">
                  <span class="timeline-event">{{ formatEventType(log.event_type) }}</span>
                  <span class="timeline-status" [ngClass]="getTimelineClass(log.event_type)">
                    {{ getStatusLabel(log.event_type) }}
                  </span>
                </div>
                <span class="timeline-time">{{ log.timestamp | date:'medium' }}</span>
                <div *ngIf="log.event_data && showEventData(log.event_type)" class="timeline-data">
                  <pre>{{ formatEventData(log.event_data) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </mat-card>

        <!-- ============================================================ -->
        <!-- SECTION 4: Validation Result -->
        <!-- ============================================================ -->
        <mat-card *ngIf="validationResult" class="section-card validation-card">
          <h3>
            <mat-icon [ngClass]="validationResult.passed ? 'check-pass' : 'check-fail'">
              {{ validationResult.passed ? 'verified' : 'gpp_bad' }}
            </mat-icon>
            Validation Result
          </h3>

          <div class="validation-status">
            <span class="validation-badge" [ngClass]="validationResult.passed ? 'pass' : 'fail'">
              {{ validationResult.passed ? 'ALL CHECKS PASSED' : 'VALIDATION FAILED' }}
            </span>
            <span *ngIf="reviewResult?.feedback_iterations" class="feedback-info">
              Feedback iterations: {{ reviewResult!.feedback_iterations }}
            </span>
          </div>

          <div class="validation-checks">
            <div *ngFor="let check of validationResult.checks" class="validation-check">
              <mat-icon [ngClass]="check.passed ? 'check-pass' : 'check-fail'">
                {{ check.passed ? 'check_circle' : 'cancel' }}
              </mat-icon>
              <div class="check-info">
                <span class="check-name">{{ formatCheckName(check.name) }}</span>
                <span class="check-message">{{ check.message }}</span>
              </div>
              <span *ngIf="check.passed" class="check-status pass">PASS</span>
              <span *ngIf="!check.passed" class="check-status fail">FAIL</span>
            </div>
          </div>
        </mat-card>

        <!-- ============================================================ -->
        <!-- SECTION 5: Purchase Order -->
        <!-- ============================================================ -->
        <mat-card *ngIf="reviewResult?.purchase_order" class="section-card">
          <h3><mat-icon>receipt_long</mat-icon> Purchase Order Created</h3>
          <div class="po-grid">
            <div class="info-row">
              <span class="info-label">PO ID</span>
              <span class="info-value mono">#{{ reviewResult!.purchase_order!.id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Quantity</span>
              <span class="info-value highlight">{{ reviewResult!.purchase_order!.quantity | number }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Unit Price</span>
              <span class="info-value">\${{ reviewResult!.purchase_order!.unit_price | number:'1.2-2' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Total Price</span>
              <span class="info-value">\${{ reviewResult!.purchase_order!.total_price | number:'1.2-2' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Status</span>
              <span class="status-badge" [ngClass]="reviewResult!.purchase_order!.status.toLowerCase()">
                {{ reviewResult!.purchase_order!.status }}
              </span>
            </div>
          </div>
        </mat-card>
      </div>

      <!-- Error -->
      <mat-card *ngIf="error" class="error-card fade-in-up">
        <mat-icon>error</mat-icon>
        <p>{{ error }}</p>
        <button mat-stroked-button (click)="error = null">Dismiss</button>
      </mat-card>
    </div>
  `,
  styles: [`
    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      h1 { font-size: 28px; font-weight: 700; margin-right: 12px; }
    }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .review-progress { margin-bottom: 24px; border-radius: 4px; }

    /* Context Grid */
    .context-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 20px;
    }

    .info-card {
      padding: 20px !important;
      h3 {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-secondary);
        margin-bottom: 16px;
        mat-icon { font-size: 18px; width: 18px; height: 18px; color: var(--accent-cyan); }
      }
    }

    .info-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--border-color);
      &:last-child { border-bottom: none; }
    }

    .info-label { color: var(--text-secondary); font-size: 13px; }
    .info-value { font-weight: 500; text-align: right; }
    .info-value.mono { font-family: 'JetBrains Mono', 'SF Mono', monospace; font-size: 13px; }
    .info-value.highlight { color: var(--accent-cyan); font-weight: 700; font-size: 16px; }

    mat-divider { margin: 12px 0; }

    /* Section cards */
    .section-card {
      padding: 24px !important;
      margin-bottom: 20px;
      h3 {
        display: flex; align-items: center; gap: 8px;
        font-size: 16px; font-weight: 600; margin-bottom: 20px;
        mat-icon { color: var(--accent-cyan); }
      }
    }

    /* Decision Row */
    .decision-row {
      display: flex;
      gap: 32px;
      flex-wrap: wrap;
      padding: 16px 0;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 20px;
    }

    .decision-item {
      display: flex; flex-direction: column; gap: 4px;
    }

    .decision-label {
      font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
      color: var(--text-secondary);
    }

    .decision-value {
      font-size: 24px; font-weight: 700;
      &.accent { color: var(--accent-cyan); }
    }

    .decision-badge {
      display: inline-block;
      font-size: 16px; font-weight: 700; padding: 6px 16px; border-radius: 6px;
      &.accept { background: rgba(52, 211, 153, 0.15); color: var(--status-accept); }
      &.modify { background: rgba(251, 191, 36, 0.15); color: var(--status-modify); }
      &.reject { background: rgba(248, 113, 113, 0.15); color: var(--status-reject); }
      &.investigate { background: rgba(96, 165, 250, 0.15); color: var(--status-investigate); }
    }

    .confidence-badge {
      font-size: 14px; font-weight: 600; padding: 6px 12px; border-radius: 6px;
      &.high { background: rgba(52, 211, 153, 0.1); color: var(--status-accept); }
      &.medium { background: rgba(251, 191, 36, 0.1); color: var(--status-modify); }
      &.low { background: rgba(248, 113, 113, 0.1); color: var(--status-reject); }
    }

    .required { color: var(--status-modify); font-weight: 600; }
    .not-required { color: var(--text-muted); font-size: 13px; }

    /* Reasoning */
    .reasoning-section, .factors-section, .constraints-section {
      margin-bottom: 16px;
      h4 {
        font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
        color: var(--text-secondary); margin-bottom: 8px;
      }
    }
    .reasoning-section p { line-height: 1.6; }
    .factors-section ul { padding-left: 20px; }
    .factors-section li { margin-bottom: 4px; line-height: 1.5; }

    .constraint-chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .constraint-chip {
      display: flex; align-items: center; gap: 4px;
      padding: 4px 12px; background: var(--bg-primary); border-radius: 20px;
      font-size: 13px; text-transform: capitalize;
      mat-icon { font-size: 16px; width: 16px; height: 16px; }
    }

    /* Approval */
    .approval-section {
      margin-top: 20px; padding-top: 20px;
      h4 {
        display: flex; align-items: center; gap: 8px;
        color: var(--status-modify); margin: 16px 0 8px;
      }
    }
    .approval-message { color: var(--text-secondary); margin-bottom: 16px; }
    .approval-actions { display: flex; gap: 12px; }

    /* Timeline */
    .timeline { padding-left: 4px; }

    .timeline-item {
      display: flex; gap: 16px; position: relative;
      padding-bottom: 16px;
    }

    .timeline-dot {
      width: 32px; height: 32px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      background: var(--bg-elevated); flex-shrink: 0; z-index: 1;
      mat-icon { font-size: 16px; width: 16px; height: 16px; color: var(--accent-cyan); }
    }

    .timeline-connector {
      position: absolute;
      left: 15px; top: 36px; bottom: 0; width: 2px;
      background: var(--border-color);
    }

    .timeline-item.success .timeline-dot { background: rgba(52, 211, 153, 0.15); }
    .timeline-item.success .timeline-dot mat-icon { color: var(--status-accept); }
    .timeline-item.error .timeline-dot { background: rgba(248, 113, 113, 0.15); }
    .timeline-item.error .timeline-dot mat-icon { color: var(--status-reject); }
    .timeline-item.warning .timeline-dot { background: rgba(251, 191, 36, 0.15); }
    .timeline-item.warning .timeline-dot mat-icon { color: var(--status-modify); }

    .timeline-content { flex: 1; min-width: 0; }
    .timeline-header { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
    .timeline-event { font-weight: 500; font-size: 14px; }
    .timeline-status {
      font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
      padding: 2px 8px; border-radius: 4px;
      &.success { background: rgba(52, 211, 153, 0.15); color: var(--status-accept); }
      &.error { background: rgba(248, 113, 113, 0.15); color: var(--status-reject); }
      &.warning { background: rgba(251, 191, 36, 0.15); color: var(--status-modify); }
    }
    .timeline-time { font-size: 12px; color: var(--text-muted); }
    .timeline-data {
      margin-top: 4px;
      pre {
        font-size: 11px; color: var(--text-secondary); background: var(--bg-primary);
        padding: 8px 12px; border-radius: 6px; overflow-x: auto; max-height: 120px;
        white-space: pre-wrap;
      }
    }

    /* Validation */
    .validation-status { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
    .validation-badge {
      padding: 8px 20px; border-radius: 6px; font-weight: 700; font-size: 13px;
      &.pass { background: rgba(52, 211, 153, 0.15); color: var(--status-accept); }
      &.fail { background: rgba(248, 113, 113, 0.15); color: var(--status-reject); }
    }
    .feedback-info { color: var(--text-secondary); font-size: 13px; }

    .validation-checks { display: flex; flex-direction: column; gap: 8px; }
    .validation-check {
      display: flex; align-items: center; gap: 12px;
      padding: 12px 16px; background: var(--bg-primary); border-radius: 8px;
      mat-icon { flex-shrink: 0; }
    }
    .check-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
    .check-name { font-weight: 600; text-transform: capitalize; }
    .check-message { font-size: 13px; color: var(--text-secondary); }
    .check-status {
      font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px;
      &.pass { background: rgba(52, 211, 153, 0.15); color: var(--status-accept); }
      &.fail { background: rgba(248, 113, 113, 0.15); color: var(--status-reject); }
    }

    /* PO grid */
    .po-grid { max-width: 500px; }

    /* Error */
    /* Scenario Card */
    .scenario-card {
      padding: 16px 20px !important;
      margin-bottom: 20px;
      background: rgba(30, 41, 59, 0.7) !important;
      border: 1px solid var(--border-color);
      border-radius: 8px;
    }
    .scenario-header {
      margin-bottom: 12px;
    }
    .scenario-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 600;
      color: var(--accent-cyan);
      margin-bottom: 4px;
      mat-icon { font-size: 18px; width: 18px; height: 18px; }
    }
    .scenario-subtitle {
      font-size: 12px;
      color: var(--text-secondary);
    }
    .scenario-buttons {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      button {
        font-size: 12px;
        font-weight: 500;
        mat-icon { font-size: 16px; width: 16px; height: 16px; margin-right: 4px; }
        &.active-scenario {
          background: rgba(6, 182, 212, 0.15) !important;
          border-color: var(--accent-cyan) !important;
          color: var(--accent-cyan) !important;
        }
      }
    }

    .error-card {
      display: flex; align-items: center; gap: 12px;
      padding: 20px !important; color: var(--status-reject);
    }

    @media (max-width: 900px) {
      .context-grid { grid-template-columns: 1fr; }
    }
  `],
})
export class RecommendationDetailComponent implements OnInit {
  recommendation: Recommendation | null = null;
  context: RecommendationContext | null = null;
  activityLogs: AgentActivityLog[] = [];
  latestDecision: AgentDecision | null = null;
  validationResult: ValidationResult | null = null;
  reviewResult: AgentReviewResponse | null = null;
  activeScenario: string | null = null;
  loading = true;
  reviewing = false;
  acting = false;
  error: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.loadRecommendation(id);
  }

  loadScenario(scenarioId: string) {
    this.activeScenario = scenarioId;
    this.loading = true;
    this.api.applyDemoScenario(scenarioId).subscribe({
      next: (res) => {
        this.snackBar.open(res.message || 'Demo scenario applied to database', 'OK', { duration: 4000 });
        this.loadRecommendation(1);
      },
      error: (err) => {
        this.error = err.error?.detail || 'Failed to apply scenario';
        this.loading = false;
      },
    });
  }

  loadRecommendation(id: number) {
    forkJoin({
      rec: this.api.getRecommendation(id),
      context: this.api.getRecommendationContext(id),
    }).subscribe({
      next: ({ rec, context }) => {
        this.recommendation = rec;
        this.context = context;
        this.activityLogs = rec.activity_logs || [];
        this.latestDecision = rec.decisions?.length
          ? rec.decisions[rec.decisions.length - 1]
          : null;
        this.loading = false;
      },
      error: () => {
        this.error = 'Failed to load recommendation';
        this.loading = false;
      },
    });
  }

  triggerReview() {
    if (!this.recommendation) return;
    this.reviewing = true;
    this.error = null;

    this.api.triggerAgentReview(this.recommendation.id).subscribe({
      next: (result) => {
        this.reviewResult = result;
        this.latestDecision = result.decision;
        if (result.validation) this.validationResult = result.validation;
        this.reviewing = false;
        this.loadRecommendation(this.recommendation!.id);
        this.snackBar.open('AI review complete', 'OK', { duration: 4000 });
      },
      error: (err) => {
        this.error = err.error?.detail || 'Agent review failed. AI service temporarily unavailable.';
        this.reviewing = false;
      },
    });
  }

  confirmApprove() {
    if (!this.recommendation) return;
    if (!confirm('Approve this purchasing action? A purchase order will be created.')) return;
    this.acting = true;
    this.api.approveRecommendation(this.recommendation.id).subscribe({
      next: () => {
        this.snackBar.open('Purchase approved — PO created', 'OK', { duration: 4000 });
        this.loadRecommendation(this.recommendation!.id);
        this.acting = false;
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Approval failed', 'OK', { duration: 4000 });
        this.acting = false;
      },
    });
  }

  confirmReject() {
    if (!this.recommendation) return;
    if (!confirm('Reject this recommendation? This cannot be undone.')) return;
    this.acting = true;
    this.api.rejectRecommendation(this.recommendation.id).subscribe({
      next: () => {
        this.snackBar.open('Recommendation rejected', 'OK', { duration: 4000 });
        this.loadRecommendation(this.recommendation!.id);
        this.acting = false;
      },
      error: () => {
        this.snackBar.open('Rejection failed', 'OK', { duration: 4000 });
        this.acting = false;
      },
    });
  }

  formatStatus(s: string): string { return s.replace(/_/g, ' '); }

  formatCheckName(name: string): string {
    const m: Record<string, string> = {
      budget: 'Budget', moq: 'Min Order Quantity', storage: 'Storage Capacity',
      supplier_availability: 'Supplier Availability', quantity: 'Quantity',
      po_validity: 'PO Validity', order_exists: 'Order Exists',
    };
    return m[name] || name;
  }

  formatEventType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  getEventIcon(type: string): string {
    const icons: Record<string, string> = {
      investigation_started: 'play_arrow', product_retrieved: 'inventory_2',
      inventory_retrieved: 'warehouse', forecast_retrieved: 'trending_up',
      open_pos_retrieved: 'receipt_long', supplier_checked: 'local_shipping',
      alternative_suppliers_checked: 'compare_arrows', budget_checked: 'account_balance_wallet',
      storage_checked: 'storage', quantity_calculated: 'calculate',
      decision_generated: 'psychology', human_approval_requested: 'verified_user',
      human_approved: 'check_circle', human_rejected: 'cancel',
      purchase_order_created: 'add_shopping_cart', purchase_order_modified: 'edit',
      purchase_order_finalized: 'done_all', purchase_order_cancelled: 'block',
      validation_passed: 'verified', validation_failed: 'error',
      agent_re_investigating: 'refresh', agent_error: 'error_outline',
    };
    return icons[type] || 'circle';
  }

  getTimelineClass(type: string): string {
    if (['validation_passed', 'human_approved', 'purchase_order_finalized'].includes(type)) return 'success';
    if (['validation_failed', 'human_rejected', 'purchase_order_cancelled', 'agent_error'].includes(type)) return 'error';
    if (['agent_re_investigating', 'human_approval_requested'].includes(type)) return 'warning';
    return '';
  }

  getStatusLabel(type: string): string {
    if (this.getTimelineClass(type) === 'success') return '✓ Success';
    if (this.getTimelineClass(type) === 'error') return '✗ Failed';
    if (this.getTimelineClass(type) === 'warning') return '⚠ Attention';
    return '✓ Done';
  }

  showEventData(type: string): boolean {
    return ['quantity_calculated', 'validation_failed', 'agent_re_investigating',
            'purchase_order_created', 'purchase_order_modified', 'agent_error'].includes(type);
  }

  formatEventData(data: any): string {
    if (!data) return '';
    return JSON.stringify(data, null, 2);
  }
}
