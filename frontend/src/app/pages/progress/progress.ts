import { Component, inject } from '@angular/core';
// import { ProgressService } from '../../core/services/onoma.services';
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
  //private readonly progressService = inject(ProgressService);
  // readonly progress = this.progressService.progress;
  readonly focus = 'Reading fluency';
}
