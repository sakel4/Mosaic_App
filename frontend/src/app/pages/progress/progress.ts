import { UserService } from '../../core/services/user-service';
import { Component, inject } from '@angular/core';
import { ProgressService } from '../../core/services/progress-service';
import { computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { KidProgress } from './kid-progress';
import { createProgressReport, downloadProgressReport } from '../../core/services/progress-report';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';
import {
  AchievementComponent,
  ProgressChartComponent,
  SkillCardComponent,
} from '../../shared/progress-widgets/progress-widgets';

@Component({
  selector: 'app-progress',
  imports: [AchievementComponent, ProgressChartComponent, SkillCardComponent, KidProgress, FormsModule],
  templateUrl: './progress.html',
  styleUrl: './progress.scss',
})
export class Progress {
  private readonly progressService = inject(ProgressService);
  readonly progress = this.progressService.progress;
  private readonly users = inject(UserService);
  readonly isChild = computed(() => this.users.profile().ageGroup === 'under_12');
  readonly reportBusy = signal(false);
  readonly reportStatus = signal('');
  private readonly http = inject(HttpClient);
  private readonly snackBar = inject(MatSnackBar);
  email = '';

  async downloadReport(sendEmail = false): Promise<void> {
    if (this.reportBusy()) return;
    this.reportBusy.set(true);
    this.reportStatus.set('');
    const recipient = this.email.trim();
    try {
      const progress = structuredClone(this.progress());
      if (sendEmail) {
        const doc = await createProgressReport(progress);
        const payload = new FormData();
        payload.append('email', recipient);
        payload.append('pdf', doc.output('blob'), 'mosaic-progress-sample.pdf');
        await firstValueFrom(this.http.post('/users/progress/email/', payload));
        this.reportStatus.set(`Progress report sent to ${recipient}.`);
        this.snackBar.open(this.reportStatus(), 'Dismiss', {
          duration: 5000,
          panelClass: ['success-snackbar'],
          verticalPosition: 'bottom',
        });
      } else {
        await downloadProgressReport(progress);
        this.reportStatus.set('Your sample progress PDF has been downloaded.');
      }
    } catch {
      this.reportStatus.set(sendEmail ? 'The report could not be emailed. Please try again.' : 'The PDF could not be downloaded. Please try again.');
    } finally {
      this.reportBusy.set(false);
    }
  }
  get focus(): string {
    return this.users.profile().currentFocus.map((focus) => focus.skill).join(', ') || 'Reading fluency, Comprehension';
  }
}
