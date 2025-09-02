import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

// Angular Material Modules
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatBadgeModule } from '@angular/material/badge';
import { MatMenuModule } from '@angular/material/menu';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatListModule } from '@angular/material/list';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatExpansionModule } from '@angular/material/expansion';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

// Core Components
import { DashboardComponent } from './components/dashboard/dashboard.component';

// Shared Components
import { NavigationComponent } from './shared/components/navigation/navigation.component';
import { HeaderComponent } from './shared/components/header/header.component';
import { LoadingSpinnerComponent } from './shared/components/loading-spinner/loading-spinner.component';

// Simple placeholders for remaining components
import { CampaignManagementComponent } from './components/campaign-management/campaign-management.component';
import { PatientListComponent } from './components/patient-list/patient-list.component';
import { WorkflowMonitorComponent } from './components/workflow-monitor/workflow-monitor.component';
import { AnalyticsDashboardComponent } from './components/analytics-dashboard/analytics-dashboard.component';

@NgModule({
  declarations: [
    AppComponent,
    DashboardComponent,
    CampaignManagementComponent,
    PatientListComponent,
    WorkflowMonitorComponent,
    AnalyticsDashboardComponent,
    NavigationComponent,
    HeaderComponent,
    LoadingSpinnerComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    
    // Angular Material Modules
    MatToolbarModule,
    MatSidenavModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatInputModule,
    MatSelectModule,
    MatFormFieldModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatBadgeModule,
    MatMenuModule,
    MatCheckboxModule,
    MatListModule,
    MatDividerModule,
    MatTooltipModule,
    MatExpansionModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }