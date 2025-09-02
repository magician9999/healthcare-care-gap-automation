import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { DashboardComponent } from './components/dashboard/dashboard.component';
import { CampaignManagementComponent } from './components/campaign-management/campaign-management.component';
import { PatientListComponent } from './components/patient-list/patient-list.component';
import { WorkflowMonitorComponent } from './components/workflow-monitor/workflow-monitor.component';
import { AnalyticsDashboardComponent } from './components/analytics-dashboard/analytics-dashboard.component';

const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'campaigns', component: CampaignManagementComponent },
  { path: 'patients', component: PatientListComponent },
  { path: 'workflows', component: WorkflowMonitorComponent },
  { path: 'analytics', component: AnalyticsDashboardComponent },
  { path: '**', redirectTo: '/dashboard' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }