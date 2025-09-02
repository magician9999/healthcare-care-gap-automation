export interface WorkflowStatus {
  workflow_id: string;
  workflow_status: string;
  current_step?: string;
  progress: number;
  started_at?: string;
  completed_at?: string;
  execution_time_seconds?: number;
  results?: any;
  errors?: string[];
}

export interface AgentStatus {
  agent_name: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  error_rate: number;
  average_response_time: number;
  last_activity?: string;
  uptime_hours: number;
}

export interface CampaignConfig {
  campaign_name: string;
  description?: string;
  filters: {
    age_min?: number;
    age_max?: number;
    screening_type?: string;
    priority_level?: string;
    limit?: number;
  };
  workflow_type: string;
  target_patients?: Patient[];
}

export interface Campaign {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'completed' | 'paused' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress: number;
  patients_processed: number;
  total_patients: number;
  success_rate: number;
  workflow_id?: string;
  config: CampaignConfig;
}

import { Patient } from './patient.model';