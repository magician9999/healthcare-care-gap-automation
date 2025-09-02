import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Patient } from '../models/patient.model';
import { WorkflowStatus, AgentStatus, Campaign, CampaignConfig } from '../models/workflow.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiUrl || 'http://localhost:8000/api/v1';
  
  // Real-time data subjects
  private agentStatusSubject = new BehaviorSubject<AgentStatus[]>([]);
  private systemHealthSubject = new BehaviorSubject<any>({});
  
  public agentStatus$ = this.agentStatusSubject.asObservable();
  public systemHealth$ = this.systemHealthSubject.asObservable();

  constructor(private http: HttpClient) {
    // Initialize real-time updates
    this.startRealtimeUpdates();
  }

  // Patient API Methods
  getPatients(params?: any): Observable<{ patients: Patient[], total: number }> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<{ patients: Patient[], total: number }>(`${this.baseUrl}/patients`, { params: httpParams });
  }

  getPatientDetails(patientId: number): Observable<Patient> {
    return this.http.get<Patient>(`${this.baseUrl}/patients/${patientId}`);
  }

  getPriorityPatients(limit: number = 20): Observable<{ prioritized_patients: Patient[], insights: any }> {
    return this.http.post<{ prioritized_patients: Patient[], insights: any }>(`${this.baseUrl}/agents/data-analyst/prioritize`, {
      filters: { limit }
    });
  }

  // Campaign & Workflow API Methods
  getCampaigns(): Observable<Campaign[]> {
    return this.http.get<Campaign[]>(`${this.baseUrl}/campaigns`);
  }

  createCampaign(config: CampaignConfig): Observable<Campaign> {
    return this.http.post<Campaign>(`${this.baseUrl}/campaigns`, config);
  }

  startWorkflow(templateName: string, context: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/workflows/start`, {
      template_name: templateName,
      context: context
    });
  }

  getWorkflowStatus(workflowId?: string): Observable<WorkflowStatus[]> {
    const url = workflowId 
      ? `${this.baseUrl}/workflows/${workflowId}/status`
      : `${this.baseUrl}/workflows/status`;
    return this.http.get<WorkflowStatus[]>(url);
  }

  getWorkflowTemplates(): Observable<any> {
    return this.http.get(`${this.baseUrl}/workflows/templates`);
  }

  // Agent API Methods
  getAgentMetrics(): Observable<{ agent_metrics: { [key: string]: AgentStatus } }> {
    return this.http.get<{ agent_metrics: { [key: string]: AgentStatus } }>(`${this.baseUrl}/agents/metrics`);
  }

  getAgentStatus(): Observable<AgentStatus[]> {
    return this.http.get<AgentStatus[]>(`${this.baseUrl}/agents/status`);
  }

  // Analytics API Methods
  getAnalytics(timeRange: string = '7d'): Observable<any> {
    return this.http.get(`${this.baseUrl}/analytics`, {
      params: { time_range: timeRange }
    });
  }

  getSystemHealth(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health`);
  }

  // Dashboard API Methods
  getDashboardData(): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboard`);
  }

  // Communication API Methods
  createOutreachMessage(patientId: number, priority: string, careGaps: any[]): Observable<any> {
    return this.http.post(`${this.baseUrl}/agents/communication-specialist/outreach`, {
      patient_id: patientId,
      priority_level: priority,
      overdue_screenings: careGaps
    });
  }

  // Real-time updates
  private startRealtimeUpdates(): void {
    // Update agent status every 30 seconds
    setInterval(() => {
      this.getAgentMetrics().subscribe(
        data => {
          const agentList = Object.entries(data.agent_metrics).map(([name, status]) => ({
            ...status,
            agent_name: name
          })) as AgentStatus[];
          this.agentStatusSubject.next(agentList);
        },
        error => console.error('Error fetching agent metrics:', error)
      );
    }, 30000);

    // Update system health every 60 seconds
    setInterval(() => {
      this.getSystemHealth().subscribe(
        data => this.systemHealthSubject.next(data),
        error => console.error('Error fetching system health:', error)
      );
    }, 60000);

    // Initial load
    this.loadInitialData();
  }

  private loadInitialData(): void {
    this.getAgentMetrics().subscribe(
      data => {
        const agentList = Object.entries(data.agent_metrics).map(([name, status]) => ({
          ...status,
          agent_name: name
        })) as AgentStatus[];
        this.agentStatusSubject.next(agentList);
      }
    );

    this.getSystemHealth().subscribe(
      data => this.systemHealthSubject.next(data)
    );
  }
}