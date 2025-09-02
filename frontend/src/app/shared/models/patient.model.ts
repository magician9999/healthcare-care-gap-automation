// Frontend models matching FastAPI backend structure

export interface Patient {
  id: number;
  name: string;
  age: number;
  email: string;
  phone?: string;
  date_of_birth: string;
  insurance_info?: { [key: string]: any };
  risk_factors?: string;
  preferred_contact_method?: string;
  total_care_gaps: number;
  open_care_gaps: number;
  priority_score?: number;
  priority_level?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  overdue_care_gaps: CareGap[];
  recent_appointments?: Appointment[];
  created_at: string;
  updated_at: string;
}

export interface CareGap {
  id: number;
  care_gap_id: number;
  screening_type: string;
  last_screening_date?: string;
  overdue_days: number;
  priority_level: 'urgent' | 'high' | 'medium' | 'low';
  status?: 'open' | 'in_progress' | 'closed' | 'cancelled';
  created_at?: string;
  updated_at?: string;
}

export interface Appointment {
  id: number;
  date: string;
  doctor_name: string;
  location: string;
  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show' | 'rescheduled';
}

// API Response models
export interface PatientListResponse {
  patients: Patient[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PatientFilters {
  search?: string;
  min_age?: number;
  max_age?: number;
  screening_type?: string;
  min_overdue_days?: number;
  max_overdue_days?: number;
  priority_level?: 'low' | 'medium' | 'high' | 'urgent';
  has_open_care_gaps?: boolean;
  preferred_contact_method?: string;
}

export interface PatientStatistics {
  total_patients: number;
  patients_with_open_gaps: number;
  total_open_care_gaps: number;
  urgent_care_gaps: number;
  high_priority_care_gaps: number;
  system_health_percentage: number;
}

// Agent workflow models
export interface WorkflowStartRequest {
  template_name: string;
  context: { [key: string]: any };
  workflow_id?: string;
}

export interface CareGapWorkflowRequest {
  filters: PatientFilters;
  workflow_options?: { [key: string]: any };
}

export interface WorkflowStatusResponse {
  status: string;
  workflow_id?: string;
  workflow_status?: string;
  current_step?: string;
  progress?: number;
  message?: string;
}

export interface AgentMetrics {
  status: string;
  service_available: boolean;
  service_status?: string;
  agents_online: number;
  active_workflows: number;
}

export interface AgentStatus {
  agent_name: string;
  status: 'idle' | 'busy' | 'offline' | 'error';
  current_task?: string;
  last_activity?: string;
  metrics?: {
    tasks_completed: number;
    average_response_time: number;
    success_rate: number;
  };
}

// Workflow template models
export interface WorkflowTemplate {
  name: string;
  description: string;
  parameters: { [key: string]: any };
  estimated_duration?: string;
}

// Real-time update models
export interface WorkflowUpdate {
  workflow_id: string;
  status: string;
  step: string;
  progress: number;
  timestamp: string;
  message?: string;
  data?: any;
}

export interface SystemHealthStatus {
  overall_status: 'healthy' | 'warning' | 'error';
  database_status: 'online' | 'offline' | 'degraded';
  agent_service_status: 'online' | 'offline' | 'degraded';
  api_response_time: number;
  active_workflows: number;
  last_updated: string;
}