import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, interval, of } from 'rxjs';
import { map, catchError, switchMap, shareReplay } from 'rxjs/operators';
import { 
  Patient, 
  PatientListResponse, 
  PatientFilters, 
  PatientStatistics,
  CareGap,
  WorkflowStartRequest,
  CareGapWorkflowRequest,
  WorkflowStatusResponse,
  AgentMetrics,
  AgentStatus,
  WorkflowTemplate,
  SystemHealthStatus
} from '../models/patient.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = 'http://localhost:8000/api/v1';
  
  // Real-time data subjects
  private agentStatusSubject = new BehaviorSubject<AgentStatus[]>([]);
  private systemHealthSubject = new BehaviorSubject<SystemHealthStatus>({
    overall_status: 'healthy',
    database_status: 'online',
    agent_service_status: 'online',
    api_response_time: 0,
    active_workflows: 0,
    last_updated: new Date().toISOString()
  });
  private activeWorkflowsSubject = new BehaviorSubject<number>(0);

  // Observable streams
  public agentStatus$ = this.agentStatusSubject.asObservable();
  public systemHealth$ = this.systemHealthSubject.asObservable();
  public activeWorkflows$ = this.activeWorkflowsSubject.asObservable();

  // Caching
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>();
  private readonly DEFAULT_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  constructor(private http: HttpClient) {
    this.startRealTimeUpdates();
  }

  // ==================== PATIENT ENDPOINTS ====================

  /**
   * Get paginated list of patients with optional filters
   */
  getPatients(
    page: number = 1,
    perPage: number = 50,
    sortBy: string = 'name',
    sortOrder: 'asc' | 'desc' = 'asc',
    filters?: PatientFilters
  ): Observable<PatientListResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString())
      .set('sort_by', sortBy)
      .set('sort_order', sortOrder);

    // Add filters
    if (filters) {
      Object.keys(filters).forEach(key => {
        const value = (filters as any)[key];
        if (value !== null && value !== undefined && value !== '') {
          params = params.set(key, value.toString());
        }
      });
    }

    const cacheKey = `patients_${params.toString()}`;
    return this.getCachedOrFetch(cacheKey, () => 
      this.http.get<PatientListResponse>(`${this.baseUrl}/patients`, { params })
    );
  }

  /**
   * Get a specific patient by ID
   */
  getPatient(patientId: number): Observable<Patient> {
    const cacheKey = `patient_${patientId}`;
    return this.getCachedOrFetch(cacheKey, () => 
      this.http.get<Patient>(`${this.baseUrl}/patients/${patientId}`)
    );
  }

  /**
   * Get care gaps for a specific patient
   */
  getPatientCareGaps(patientId: number, status?: string): Observable<CareGap[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }

    const cacheKey = `patient_care_gaps_${patientId}_${status || 'all'}`;
    return this.getCachedOrFetch(cacheKey, () => 
      this.http.get<CareGap[]>(`${this.baseUrl}/patients/${patientId}/care-gaps`, { params })
    );
  }

  /**
   * Get patient statistics for dashboard
   */
  getPatientStatistics(): Observable<PatientStatistics> {
    const cacheKey = 'patient_statistics';
    return this.getCachedOrFetch(cacheKey, () => 
      this.http.get<PatientStatistics>(`${this.baseUrl}/patients/statistics/overview`)
    );
  }

  // ==================== AGENT WORKFLOW ENDPOINTS ====================

  /**
   * Check agent service health
   */
  getAgentHealth(): Observable<AgentMetrics> {
    return this.http.get<AgentMetrics>(`${this.baseUrl}/agents/health`);
  }

  /**
   * Get available workflow templates
   */
  getWorkflowTemplates(): Observable<WorkflowTemplate[]> {
    const cacheKey = 'workflow_templates';
    return this.getCachedOrFetch(cacheKey, () => 
      this.http.get<WorkflowTemplate[]>(`${this.baseUrl}/agents/templates`)
    , this.DEFAULT_CACHE_TTL * 2); // Cache longer for templates
  }

  /**
   * Start a new workflow
   */
  startWorkflow(request: WorkflowStartRequest): Observable<any> {
    return this.http.post(`${this.baseUrl}/agents/workflows/start`, request);
  }

  /**
   * Start care gap automation workflow
   */
  startCareGapWorkflow(request: CareGapWorkflowRequest): Observable<any> {
    return this.http.post(`${this.baseUrl}/agents/workflows/care-gap`, request);
  }

  /**
   * Start urgent patient workflow
   */
  startUrgentWorkflow(filters: PatientFilters): Observable<any> {
    return this.http.post(`${this.baseUrl}/agents/workflows/urgent`, filters);
  }

  /**
   * Get workflow status
   */
  getWorkflowStatus(workflowId?: string): Observable<WorkflowStatusResponse> {
    const url = workflowId 
      ? `${this.baseUrl}/agents/workflows/${workflowId}/status`
      : `${this.baseUrl}/agents/workflows/status`;
    
    return this.http.get<WorkflowStatusResponse>(url);
  }

  /**
   * Get all workflows status
   */
  getAllWorkflowsStatus(): Observable<any> {
    return this.http.get(`${this.baseUrl}/agents/workflows/status`);
  }

  /**
   * Get agent performance metrics
   */
  getAgentMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/agents/metrics`);
  }

  /**
   * Analyze patients using DataAnalyst agent
   */
  analyzePatients(filters: PatientFilters): Observable<any> {
    return this.http.post(`${this.baseUrl}/agents/analyze`, filters);
  }

  /**
   * Create patient communications
   */
  createPatientCommunications(patientIds: number[], priorityLevel: string = 'medium'): Observable<any> {
    return this.http.post(`${this.baseUrl}/agents/communicate`, patientIds, {
      params: { priority_level: priorityLevel }
    });
  }

  // ==================== SYSTEM HEALTH ENDPOINTS ====================

  /**
   * Check overall system health
   */
  getSystemHealth(): Observable<any> {
    return this.http.get(`${this.baseUrl}/../health`);
  }

  /**
   * Get API status
   */
  getApiStatus(): Observable<any> {
    return this.http.get(`${this.baseUrl}/status`);
  }

  // ==================== REAL-TIME DATA METHODS ====================

  /**
   * Start real-time updates for agent status and system health
   */
  private startRealTimeUpdates(): void {
    // Update agent metrics every 10 seconds
    interval(10000).pipe(
      switchMap(() => this.getAgentHealth()),
      catchError(error => {
        console.warn('Failed to get agent health:', error);
        return of(null);
      })
    ).subscribe(metrics => {
      if (metrics) {
        this.updateAgentStatus(metrics);
        this.activeWorkflowsSubject.next(metrics.active_workflows || 0);
      }
    });

    // Update system health every 30 seconds
    interval(30000).pipe(
      switchMap(() => this.getSystemHealth()),
      catchError(error => {
        console.warn('Failed to get system health:', error);
        return of(null);
      })
    ).subscribe(health => {
      if (health) {
        this.updateSystemHealth(health);
      }
    });
  }

  /**
   * Update agent status from metrics
   */
  private updateAgentStatus(metrics: AgentMetrics): void {
    const mockAgents: AgentStatus[] = [
      {
        agent_name: 'DataAnalyst',
        status: metrics.service_available ? 'idle' : 'offline',
        current_task: metrics.active_workflows > 0 ? 'Analyzing patient data' : undefined,
        last_activity: new Date().toISOString(),
        metrics: {
          tasks_completed: Math.floor(Math.random() * 50) + 10,
          average_response_time: Math.random() * 2 + 1,
          success_rate: Math.random() * 10 + 90
        }
      },
      {
        agent_name: 'CommunicationSpecialist',
        status: metrics.service_available ? 'idle' : 'offline',
        current_task: metrics.active_workflows > 1 ? 'Creating patient communications' : undefined,
        last_activity: new Date().toISOString(),
        metrics: {
          tasks_completed: Math.floor(Math.random() * 30) + 5,
          average_response_time: Math.random() * 3 + 2,
          success_rate: Math.random() * 5 + 95
        }
      },
      {
        agent_name: 'CareManager',
        status: metrics.service_available ? 'idle' : 'offline',
        current_task: metrics.active_workflows > 2 ? 'Orchestrating care workflows' : undefined,
        last_activity: new Date().toISOString(),
        metrics: {
          tasks_completed: Math.floor(Math.random() * 20) + 8,
          average_response_time: Math.random() * 1.5 + 0.5,
          success_rate: Math.random() * 8 + 92
        }
      }
    ];

    this.agentStatusSubject.next(mockAgents);
  }

  /**
   * Update system health status
   */
  private updateSystemHealth(healthData: any): void {
    const status: SystemHealthStatus = {
      overall_status: healthData.status === 'healthy' ? 'healthy' : 'warning',
      database_status: 'online', // Would come from actual health check
      agent_service_status: healthData.debug ? 'online' : 'degraded',
      api_response_time: Math.random() * 200 + 50, // Mock response time
      active_workflows: this.activeWorkflowsSubject.value,
      last_updated: new Date().toISOString()
    };

    this.systemHealthSubject.next(status);
  }

  // ==================== CACHING UTILITIES ====================

  /**
   * Get cached data or fetch from API
   */
  private getCachedOrFetch<T>(key: string, fetchFn: () => Observable<T>, ttl: number = this.DEFAULT_CACHE_TTL): Observable<T> {
    const cached = this.cache.get(key);
    const now = Date.now();

    if (cached && now - cached.timestamp < cached.ttl) {
      return of(cached.data);
    }

    return fetchFn().pipe(
      map(data => {
        this.cache.set(key, { data, timestamp: now, ttl });
        return data;
      }),
      shareReplay(1)
    );
  }

  /**
   * Clear cache for specific key or all cache
   */
  clearCache(key?: string): void {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Invalidate patient-related cache
   */
  invalidatePatientCache(): void {
    const keysToDelete = Array.from(this.cache.keys()).filter(key => 
      key.startsWith('patient') || key.includes('statistics')
    );
    keysToDelete.forEach(key => this.cache.delete(key));
  }

  // ==================== UTILITY METHODS ====================

  /**
   * Format error messages for display
   */
  formatErrorMessage(error: any): string {
    if (error.message) {
      return error.message;
    }
    if (error.detail) {
      return Array.isArray(error.detail) ? error.detail.join(', ') : error.detail;
    }
    return 'An unexpected error occurred';
  }

  /**
   * Check if API is available
   */
  isApiAvailable(): Observable<boolean> {
    return this.getApiStatus().pipe(
      map(() => true),
      catchError(() => of(false))
    );
  }

  // ==================== BACKWARD COMPATIBILITY METHODS ====================

  /**
   * Legacy method for existing components
   */
  getLegacyPatients(params?: any): Observable<{ patients: Patient[], total: number }> {
    const filters: PatientFilters = {};
    let page = 1;
    let perPage = 50;

    if (params) {
      page = params.page || 1;
      perPage = params.per_page || params.limit || 50;
      
      // Map old parameters to new filter structure
      if (params.search) filters.search = params.search;
      if (params.min_age) filters.min_age = params.min_age;
      if (params.max_age) filters.max_age = params.max_age;
      if (params.screening_type) filters.screening_type = params.screening_type;
      if (params.priority_level) filters.priority_level = params.priority_level;
    }

    return this.getPatients(page, perPage, 'name', 'asc', filters).pipe(
      map(response => ({
        patients: response.patients,
        total: response.total
      }))
    );
  }

  /**
   * Legacy method - get patient details
   */
  getPatientDetails(patientId: number): Observable<Patient> {
    return this.getPatient(patientId);
  }

  /**
   * Get dashboard data for backward compatibility
   */
  getDashboardData(): Observable<any> {
    return this.getPatientStatistics();
  }
}