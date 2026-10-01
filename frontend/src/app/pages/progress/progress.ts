import { UserService } from '../../core/services/user-service';
import { Component, inject } from '@angular/core';
import { ProgressService } from '../../core/services/progress-service';
import { computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { KidProgress } from './kid-progress';
import { downloadProgressReport, progressEmailDraft } from '../../core/services/progress-report';
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
  readonly draftLink = signal('');
  email = '';

  async downloadReport(prepareEmail = false): Promise<void> {
    if (this.reportBusy()) return;
    this.reportBusy.set(true);
    this.reportStatus.set('');
    this.draftLink.set('');
    try {
      await downloadProgressReport(structuredClone(this.progress()));
      if (prepareEmail) this.draftLink.set(progressEmailDraft(this.email.trim()));
      this.reportStatus.set(prepareEmail
        ? 'PDF downloaded. Open your email draft below, then attach the PDF before sending.'
        : 'Your sample progress PDF has been downloaded.');
    } catch {
      this.reportStatus.set('The PDF could not be downloaded. Please try again.');
    } finally {
      this.reportBusy.set(false);
    }
  }
  get focus(): string {
    return this.users.profile().currentFocus.map((focus) => focus.skill).join(', ') || 'Reading fluency, Comprehension';
  }
}
