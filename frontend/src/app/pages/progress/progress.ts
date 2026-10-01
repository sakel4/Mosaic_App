import { UserService } from '../../core/services/user-service';
import { Component, inject } from '@angular/core';
import { ProgressService } from '../../core/services/progress-service';
import {
  AchievementComponent,
  ProgressChartComponent,
  SkillCardComponent,
} from '../../shared/progress-widgets/progress-widgets';

@Component({
  selector: 'app-progress',
  imports: [AchievementComponent, ProgressChartComponent, SkillCardComponent],
  templateUrl: './progress.html',
  styleUrl: './progress.scss',
})
export class Progress {
  private readonly progressService = inject(ProgressService);
  readonly progress = this.progressService.progress;
  private readonly users = inject(UserService);
  get focus(): string {
    return this.users.profile().currentFocus.map((focus) => focus.skill).join(', ');
  }
}
