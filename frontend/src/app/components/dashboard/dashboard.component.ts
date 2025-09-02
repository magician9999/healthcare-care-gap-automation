import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../shared/services/api.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  
  loading = true;
  dashboardData = {
    activeWorkflows: 3,
    patientsProcessed: 25,
    pendingCareGaps: 42,
    systemHealth: '98%'
  };

  constructor(private apiService: ApiService) { }

  ngOnInit(): void {
    // Simulate loading
    setTimeout(() => {
      this.loading = false;
    }, 1000);
  }
}