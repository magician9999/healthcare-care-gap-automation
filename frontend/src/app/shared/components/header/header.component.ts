import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { AgentStatus } from '../../models/workflow.model';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  currentRoute: string = '';
  routeTitle: string = 'Dashboard';
  agentStatuses: AgentStatus[] = [];
  currentTime: string = '';

  private routeTitles: { [key: string]: string } = {
    '/dashboard': 'Dashboard',
    '/campaigns': 'Campaign Management',
    '/patients': 'Patient Management',
    '/workflows': 'Workflow Monitor',
    '/analytics': 'Analytics Dashboard'
  };

  constructor(
    private router: Router,
    private apiService: ApiService
  ) { }

  ngOnInit(): void {
    this.updateRouteInfo();
    this.router.events.subscribe(() => {
      this.updateRouteInfo();
    });

    // Update current time
    this.updateTime();
    setInterval(() => this.updateTime(), 1000);

    // Subscribe to agent status updates
    this.apiService.agentStatus$
      .pipe(takeUntil(this.destroy$))
      .subscribe(statuses => {
        this.agentStatuses = statuses;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private updateRouteInfo(): void {
    this.currentRoute = this.router.url;
    this.routeTitle = this.routeTitles[this.currentRoute] || 'Healthcare AutoGen';
  }

  private updateTime(): void {
    this.currentTime = new Date().toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  getAgentStatusColor(status: string): string {
    switch (status) {
      case 'idle': return 'primary';
      case 'busy': return 'accent';
      case 'error': return 'warn';
      default: return 'basic';
    }
  }

  getOverallSystemHealth(): string {
    if (this.agentStatuses.length === 0) return 'loading';
    
    const hasErrors = this.agentStatuses.some(agent => agent.status === 'error');
    const hasBusy = this.agentStatuses.some(agent => agent.status === 'busy');
    
    if (hasErrors) return 'error';
    if (hasBusy) return 'busy';
    return 'healthy';
  }

  getSystemHealthIcon(): string {
    const health = this.getOverallSystemHealth();
    switch (health) {
      case 'healthy': return 'check_circle';
      case 'busy': return 'sync';
      case 'error': return 'error';
      default: return 'help';
    }
  }

  getCurrentDate(): string {
    return new Date().toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  refreshData(): void {
    // Trigger manual refresh of dashboard data
    window.location.reload();
  }
}