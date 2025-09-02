import { Component } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-campaign-wizard-dialog',
  template: `
    <h2 mat-dialog-title>Campaign Wizard</h2>
    <mat-dialog-content>
      <p>Campaign wizard implementation coming soon...</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="close()">Close</button>
    </mat-dialog-actions>
  `
})
export class CampaignWizardDialogComponent {
  constructor(public dialogRef: MatDialogRef<CampaignWizardDialogComponent>) { }

  close(): void {
    this.dialogRef.close();
  }
}