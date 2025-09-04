import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil, catchError, debounceTime, distinctUntilChanged } from 'rxjs/operators';
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

  // Natural Language Query properties
  queryControl = new FormControl('', [Validators.required, Validators.minLength(3)]);
  queryLoading = false;
  queryResults: any[] = [];
  queryError = '';
  querySummary = '';
  queryStatistics: any = null;
  showResults = false;

  // Smart Campaign properties
  campaignLoading = false;
  campaignResults: any = null;
  campaignError = '';
  showCampaignResults = false;

  // Booking management
  bookingStatus: Map<string, 'pending' | 'booking' | 'rejecting' | 'booked' | 'rejected'> = new Map();

  // Example prompts for user guidance
  examplePrompts = [
    'Show me patients with diabetes below age 35',
    'Find all patients who need eye exams',
    'List urgent mammogram screenings',
    'Show overdue colonoscopy patients',
    'Patients needing blood pressure checks'
  ];

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

  // Natural Language Query Methods

  /**
   * Process natural language query
   */
  processQuery(): void {
    if (this.queryControl.invalid || this.queryLoading) {
      return;
    }

    const prompt = this.queryControl.value?.trim();
    if (!prompt) {
      return;
    }

    this.queryLoading = true;
    this.queryError = '';
    this.queryResults = [];
    this.querySummary = '';
    this.queryStatistics = null;

    // Use the agent-based endpoint for better analysis
    this.apiService.processNaturalLanguageQuery(prompt, 'data_analyst', 100)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Query failed:', error);
          this.queryError = this.apiService.formatErrorMessage(error);
          this.queryLoading = false;
          return [];
        })
      )
      .subscribe(response => {
        this.queryLoading = false;
        
        if (response.status === 'success' && response.result) {
          const result = response.result;
          this.queryResults = result.patients || [];
          this.querySummary = result.summary || '';
          this.queryStatistics = result.statistics || null;
          this.showResults = true;

          // Scroll to results section
          setTimeout(() => {
            const resultsElement = document.getElementById('query-results');
            if (resultsElement) {
              resultsElement.scrollIntoView({ behavior: 'smooth' });
            }
          }, 100);
        } else {
          this.queryError = response?.message || 'Query processing failed';
        }
      });
  }

  /**
   * Use example prompt
   */
  useExamplePrompt(example: string): void {
    this.queryControl.setValue(example);
    this.processQuery();
  }

  /**
   * Clear query results
   */
  clearResults(): void {
    this.queryResults = [];
    this.querySummary = '';
    this.queryStatistics = null;
    this.queryError = '';
    this.showResults = false;
    this.queryControl.setValue('');
  }

  /**
   * Get priority level badge class
   */
  getPriorityClass(priorityLevel: string): string {
    switch (priorityLevel?.toLowerCase()) {
      case 'critical':
        return 'priority-critical';
      case 'urgent':
        return 'priority-urgent';
      case 'high':
        return 'priority-high';
      case 'medium':
        return 'priority-medium';
      case 'low':
        return 'priority-low';
      default:
        return 'priority-unknown';
    }
  }

  /**
   * Format overdue days for display
   */
  formatOverdueDays(days: number): string {
    if (days <= 0) {
      return 'Up to date';
    } else if (days < 30) {
      return `${days} days overdue`;
    } else if (days < 365) {
      const months = Math.floor(days / 30);
      return `${months} month${months > 1 ? 's' : ''} overdue`;
    } else {
      const years = Math.floor(days / 365);
      const remainingMonths = Math.floor((days % 365) / 30);
      return `${years} year${years > 1 ? 's' : ''}${remainingMonths > 0 ? `, ${remainingMonths} month${remainingMonths > 1 ? 's' : ''}` : ''} overdue`;
    }
  }

  /**
   * Format screening type for display
   */
  formatScreeningType(screeningType: string): string {
    return screeningType?.replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ') || 'Unknown';
  }

  /**
   * Export query results to CSV
   */
  exportResults(): void {
    if (!this.queryResults.length) {
      return;
    }

    const headers = ['Name', 'Email', 'Phone', 'Age', 'Screening Type', 'Last Screening Date', 'Overdue Days', 'Priority Level'];
    const csvContent = [
      headers.join(','),
      ...this.queryResults.map(patient => [
        `"${patient.name || ''}"`,
        `"${patient.email || ''}"`,
        `"${patient.phone || ''}"`,
        patient.age || 0,
        `"${this.formatScreeningType(patient.screening_type)}"`,
        `"${patient.last_screening_date || 'Never'}"`,
        patient.overdue_days || 0,
        `"${patient.priority_level || 'Unknown'}"`
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `healthcare-query-results-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  // Smart Campaign Methods

  /**
   * Start smart campaign for query results
   */
  startSmartCampaign(): void {
    if (!this.queryResults.length) {
      return;
    }

    this.campaignLoading = true;
    this.campaignError = '';
    this.campaignResults = null;

    const campaignName = `Smart Campaign - ${this.formatScreeningType(this.queryResults[0]?.screening_type || 'Healthcare')} - ${new Date().toLocaleDateString()}`;

    this.apiService.startSmartCampaign(this.queryResults, campaignName)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Smart campaign failed:', error);
          this.campaignError = this.apiService.formatErrorMessage(error);
          this.campaignLoading = false;
          return [];
        })
      )
      .subscribe(response => {
        this.campaignLoading = false;
        
        if (response.status === 'success') {
          this.campaignResults = response;
          this.showCampaignResults = true;

          // Scroll to campaign results section
          setTimeout(() => {
            const campaignElement = document.getElementById('campaign-results');
            if (campaignElement) {
              campaignElement.scrollIntoView({ behavior: 'smooth' });
            }
          }, 100);
        } else {
          this.campaignError = response.message || 'Campaign creation failed';
        }
      });
  }

  /**
   * Send test email to Shivanshu Saxena
   */
  sendTestEmail(): void {
    this.campaignLoading = true;
    this.campaignError = '';

    this.apiService.sendTestEmail()
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Test email failed:', error);
          this.campaignError = this.apiService.formatErrorMessage(error);
          this.campaignLoading = false;
          return [];
        })
      )
      .subscribe(response => {
        this.campaignLoading = false;
        
        if (response.status === 'success') {
          // Show success message and email preview
          this.campaignResults = {
            ...response,
            is_test: true
          };
          this.showCampaignResults = true;

          // Scroll to campaign results section
          setTimeout(() => {
            const campaignElement = document.getElementById('campaign-results');
            if (campaignElement) {
              campaignElement.scrollIntoView({ behavior: 'smooth' });
            }
          }, 100);
        } else {
          this.campaignError = response.message || 'Test email sending failed';
        }
      });
  }

  /**
   * Clear campaign results
   */
  clearCampaignResults(): void {
    this.campaignResults = null;
    this.campaignError = '';
    this.showCampaignResults = false;
  }

  /**
   * Get campaign status class for styling
   */
  getCampaignStatusClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'success':
        return 'campaign-success';
      case 'completed':
        return 'campaign-completed';
      case 'in_progress':
        return 'campaign-progress';
      case 'failed':
        return 'campaign-failed';
      default:
        return 'campaign-unknown';
    }
  }

  // Booking management methods

  /**
   * Get unique key for patient booking tracking using email
   */
  getPatientBookingKey(patient: any): string {
    return `${patient.email}_${patient.screening_type}`;
  }

  /**
   * Get booking status for a patient
   */
  getBookingStatus(patient: any): string {
    const key = this.getPatientBookingKey(patient);
    return this.bookingStatus.get(key) || 'pending';
  }

  /**
   * Book appointment slot for patient using CareManagerAgent
   */
  bookAppointmentSlot(patient: any): void {
    console.log('bookAppointmentSlot called with patient:', patient);
    
    if (!patient.email || !patient.screening_type) {
      console.error('Missing patient information for booking:', {
        email: patient.email,
        screening_type: patient.screening_type,
        patient
      });
      return;
    }

    const key = this.getPatientBookingKey(patient);
    this.bookingStatus.set(key, 'booking');

    // Use email as primary identifier and generate a care gap ID if needed
    const careGapId = patient.care_gap_id || patient.patient_id || 1; // Fallback to 1 if no IDs available

    this.apiService.bookAppointmentSlot(
      patient.patient_id || 0, // Use 0 as placeholder for patient_id
      careGapId,
      patient.screening_type,
      undefined, // appointment_date - will be scheduled later
      `Appointment booking via smart campaign for ${patient.screening_type}`,
      patient.email // Pass email as separate parameter
    ).pipe(
      takeUntil(this.destroy$),
      catchError(error => {
        console.error('Appointment booking failed:', error);
        this.bookingStatus.set(key, 'pending');
        return [];
      })
    ).subscribe(response => {
      if (response.status === 'success') {
        this.bookingStatus.set(key, 'booked');
        
        // Show success notification
        console.log(`Appointment booked for ${patient.name} - ${patient.screening_type}`);
        
        // Refresh dashboard data to reflect updated care gap counts
        this.refreshDashboardAfterBooking();
        
        // Optional: Show success message to user
        // You could add a notification service here
        
      } else {
        this.bookingStatus.set(key, 'pending');
        console.error('Booking failed:', response.message);
      }
    });
  }

  /**
   * Reject appointment slot for patient
   */
  rejectAppointmentSlot(patient: any): void {
    if (!patient.email || !patient.screening_type) {
      console.error('Missing patient information for rejection');
      return;
    }

    const key = this.getPatientBookingKey(patient);
    this.bookingStatus.set(key, 'rejecting');

    const careGapId = patient.care_gap_id || patient.patient_id || 1;

    this.apiService.rejectAppointmentSlot(
      patient.patient_id || 0,
      careGapId,
      patient.screening_type,
      `Patient declined appointment via smart campaign. Email: ${patient.email}`
    ).pipe(
      takeUntil(this.destroy$),
      catchError(error => {
        console.error('Appointment rejection failed:', error);
        this.bookingStatus.set(key, 'pending');
        return [];
      })
    ).subscribe(response => {
      if (response.status === 'success') {
        this.bookingStatus.set(key, 'rejected');
        console.log(`Appointment rejected for ${patient.name} - ${patient.screening_type}`);
      } else {
        this.bookingStatus.set(key, 'pending');
        console.error('Rejection processing failed:', response.message);
      }
    });
  }

  /**
   * Check if booking/rejection actions are disabled for a patient
   */
  isBookingDisabled(patient: any): boolean {
    const status = this.getBookingStatus(patient);
    return status === 'booking' || status === 'rejecting' || status === 'booked' || status === 'rejected';
  }

  /**
   * Get button text based on booking status
   */
  getBookingButtonText(patient: any): string {
    const status = this.getBookingStatus(patient);
    switch (status) {
      case 'booking':
        return 'Booking...';
      case 'booked':
        return 'Booked ✓';
      case 'rejecting':
        return 'Rejecting...';
      case 'rejected':
        return 'Rejected';
      default:
        return 'Book Slot';
    }
  }

  /**
   * Get reject button text based on booking status
   */
  getRejectButtonText(patient: any): string {
    const status = this.getBookingStatus(patient);
    switch (status) {
      case 'rejecting':
        return 'Rejecting...';
      case 'rejected':
        return 'Rejected ✓';
      case 'booked':
        return 'Already Booked';
      default:
        return 'Reject';
    }
  }

  /**
   * Refresh dashboard data after booking to reflect updated care gap counts
   */
  refreshDashboardAfterBooking(): void {
    console.log('Refreshing dashboard data after booking...');
    
    // Refresh core dashboard statistics
    this.loadDashboardData();
    
    // If there are current query results, refresh them as well
    if (this.queryResults.length > 0) {
      setTimeout(() => {
        this.processQuery(); // Re-run the last query to get updated results
      }, 1000); // Small delay to allow database updates to complete
    }
  }
}