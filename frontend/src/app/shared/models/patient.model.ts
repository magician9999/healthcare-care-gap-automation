export interface Patient {
  patient_id: number;
  name: string;
  age: number;
  email: string;
  phone?: string;
  date_of_birth: string;
  risk_factors?: string;
  preferred_contact_method?: string;
  overdue_care_gaps: CareGap[];
  total_care_gaps: number;
  open_care_gaps: number;
  priority_score?: number;
  priority_level?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  clinical_reasoning?: string[];
  recommended_actions?: string[];
  recent_appointments?: Appointment[];
}

export interface CareGap {
  care_gap_id: number;
  screening_type: string;
  last_screening_date?: string;
  overdue_days: number;
  priority_level: 'urgent' | 'high' | 'medium' | 'low';
}

export interface Appointment {
  id: number;
  date: string;
  doctor_name: string;
  location: string;
  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'no_show' | 'rescheduled';
}