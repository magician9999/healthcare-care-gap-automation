import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../shared/services/api.service';
import { Patient } from '../../shared/models/patient.model';

@Component({
  selector: 'app-patient-list',
  templateUrl: './patient-list.component.html',
  styleUrls: ['./patient-list.component.scss']
})
export class PatientListComponent implements OnInit {
  
  patients: Patient[] = [];
  loading = false;
  displayedColumns = ['name', 'age', 'priorityScore', 'careGaps', 'actions'];

  constructor(private apiService: ApiService) { }

  ngOnInit(): void {
    this.loadPatients();
  }

  loadPatients(): void {
    this.loading = true;
    // Mock data for now
    setTimeout(() => {
      this.patients = [
        {
          patient_id: 1,
          name: 'John Smith',
          age: 65,
          email: 'john.smith@email.com',
          date_of_birth: '1958-03-15',
          priority_score: 85,
          priority_level: 'HIGH',
          total_care_gaps: 2,
          open_care_gaps: 2,
          overdue_care_gaps: [
            { 
              care_gap_id: 1,
              screening_type: 'Mammography', 
              overdue_days: 45,
              priority_level: 'high'
            },
            { 
              care_gap_id: 2,
              screening_type: 'Colonoscopy', 
              overdue_days: 30,
              priority_level: 'high'
            }
          ]
        },
        {
          patient_id: 2,
          name: 'Mary Johnson',
          age: 58,
          email: 'mary.johnson@email.com',
          date_of_birth: '1965-07-22',
          priority_score: 72,
          priority_level: 'MEDIUM',
          total_care_gaps: 1,
          open_care_gaps: 1,
          overdue_care_gaps: [
            { 
              care_gap_id: 3,
              screening_type: 'Annual Wellness Visit', 
              overdue_days: 20,
              priority_level: 'medium'
            }
          ]
        }
      ];
      this.loading = false;
    }, 1000);
  }

  viewPatient(patient: Patient): void {
    console.log('View patient:', patient);
  }

  contactPatient(patient: Patient): void {
    console.log('Contact patient:', patient);
  }
}