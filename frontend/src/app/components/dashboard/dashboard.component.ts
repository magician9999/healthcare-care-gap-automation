import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil, catchError } from 'rxjs/operators';
import { ApiService } from '../../shared/services/api.service';
import { WebSocketService } from '../../shared/services/websocket.service';
import { PatientStatistics, AgentStatus, SystemHealthStatus } from '../../shared/models/patient.model';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  
  loading = true;
  dashboardData: PatientStatistics = {
    total_patients: 0,
    patients_with_open_gaps: 0,
    total_open_care_gaps: 0,
    urgent_care_gaps: 0,
    high_priority_care_gaps: 0,
    system_health_percentage: 98.5
  };

  agentStatuses: AgentStatus[] = [];
  systemHealth: SystemHealthStatus | null = null;
  activeWorkflows = 0;

  private destroy$ = new Subject<void>();

  constructor(
    private apiService: ApiService,
    private webSocketService: WebSocketService
  ) { }

  ngOnInit(): void {
    this.loadDashboardData();
    this.subscribeToRealTimeUpdates();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadDashboardData(): void {
    this.loading = true;

    // Load patient statistics
    this.apiService.getPatientStatistics()
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Failed to load patient statistics:', error);
          // Use fallback data
          return [{
            total_patients: 156,
            patients_with_open_gaps: 89,
            total_open_care_gaps: 267,
            urgent_care_gaps: 23,
            high_priority_care_gaps: 45,
            system_health_percentage: 98.5
          }];
        })
      )
      .subscribe(stats => {
        this.dashboardData = stats;
        this.loading = false;
      });
  }

  subscribeToRealTimeUpdates(): void {
    // Subscribe to agent status updates
    this.apiService.agentStatus$
      .pipe(takeUntil(this.destroy$))
      .subscribe(agents => {
        this.agentStatuses = agents;
      });

    // Subscribe to system health updates
    this.apiService.systemHealth$
      .pipe(takeUntil(this.destroy$))
      .subscribe(health => {
        this.systemHealth = health;
      });

    // Subscribe to active workflows count
    this.apiService.activeWorkflows$
      .pipe(takeUntil(this.destroy$))
      .subscribe(count => {
        this.activeWorkflows = count;
      });

    // Subscribe to WebSocket updates
    this.webSocketService.getWorkflowUpdates()
      .pipe(takeUntil(this.destroy$))
      .subscribe(update => {
        console.log('Workflow update received:', update);
        // Handle workflow updates - could trigger data refresh
        this.refreshData();
      });
  }

  refreshData(): void {
    this.apiService.clearCache('patient_statistics');
    this.loadDashboardData();
  }

  startCareGapWorkflow(): void {
    this.loading = true;
    const request = {
      filters: {
        has_open_care_gaps: true,
        priority_level: 'high' as const
      },
      workflow_options: {
        auto_execute: true
      }
    };

    this.apiService.startCareGapWorkflow(request)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Failed to start care gap workflow:', error);
          this.loading = false;
          return [];
        })
      )
      .subscribe(result => {
        console.log('Care gap workflow started:', result);
        this.loading = false;
        // Subscribe to this specific workflow
        if (result.workflow_id) {
          this.webSocketService.subscribeToWorkflow(result.workflow_id);
        }
      });
  }

  startUrgentWorkflow(): void {
    const filters = {
      priority_level: 'urgent' as const,
      has_open_care_gaps: true
    };

    this.apiService.startUrgentWorkflow(filters)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Failed to start urgent workflow:', error);
          return [];
        })
      )
      .subscribe(result => {
        console.log('Urgent workflow started:', result);
        if (result.workflow_id) {
          this.webSocketService.subscribeToWorkflow(result.workflow_id);
        }
      });
  }

  analyzePatients(): void {
    const filters = {
      has_open_care_gaps: true
    };

    this.apiService.analyzePatients(filters)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Failed to analyze patients:', error);
          return [];
        })
      )
      .subscribe(result => {
        console.log('Patient analysis completed:', result);
      });
  }

  getSystemHealthClass(): string {
    if (!this.systemHealth) return 'health-unknown';
    
    switch (this.systemHealth.overall_status) {
      case 'healthy':
        return 'health-good';
      case 'warning':
        return 'health-warning';
      case 'error':
        return 'health-error';
      default:
        return 'health-unknown';
    }
  }

  getAgentStatusClass(agent: AgentStatus): string {
    switch (agent.status) {
      case 'idle':
        return 'agent-idle';
      case 'busy':
        return 'agent-busy';
      case 'offline':
        return 'agent-offline';
      case 'error':
        return 'agent-error';
      default:
        return 'agent-unknown';
    }
  }
}