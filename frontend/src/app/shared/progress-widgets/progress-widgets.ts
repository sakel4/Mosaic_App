import { Component, input } from '@angular/core';
import { LearnerSkill } from '../../core/models/learner-skill.model';

@Component({
  selector: 'app-progress-bar',
  templateUrl: './progress-bar.html',
  styleUrl: './progress-bar.scss',
})
export class ProgressBarComponent {
  readonly value = input.required<number>();
  readonly label = input.required<string>();
}

@Component({
  selector: 'app-skill-card',
  imports: [ProgressBarComponent],
  templateUrl: './skill-card.html',
  styleUrl: './skill-card.scss',
})
export class SkillCardComponent {
  readonly skill = input.required<LearnerSkill>();
}

@Component({
  selector: 'app-progress-chart',
  templateUrl: './progress-chart.html',
  styleUrl: './progress-chart.scss',
})
export class ProgressChartComponent {}

@Component({
  selector: 'app-achievement-card',
  templateUrl: './achievement-card.html',
  styleUrl: './achievement-card.scss',
})
export class AchievementComponent {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly icon = input.required<string>();
}

@Component({
  selector: 'app-progress-widgets',
  templateUrl: './progress-widgets.html',
  styleUrl: './progress-widgets.scss',
})
export class ProgressWidgets {}
