import { Component, input } from '@angular/core';
import { LearnerSkill } from '../../core/models/learner-skill.model';
import { ElementRef, computed, effect, inject, viewChild } from '@angular/core';
import { Progress } from '../../core/models/progress.model';
import Chart from 'chart.js/auto';
import { ProgressService } from '../../core/services/progress-service';

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
export class ProgressChartComponent {
  private readonly savedProgress = inject(ProgressService).progress;
  readonly data = input<Progress>();
  readonly progress = computed(() => this.data() ?? this.savedProgress());
  readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('chart');

  constructor() {
    effect((onCleanup) => {
      const canvas = this.canvas()?.nativeElement;
      const history = this.progress().history ?? [];
      if (!canvas || !history.some((day) => day.completed > 0)) return;
      const root = document.documentElement;
      const render = () => {
        const style = getComputedStyle(root);
        const color = (name: string) => style.getPropertyValue(name).trim();
        return new Chart(canvas, {
          type: 'line',
          data: {
            labels: history.map((day) => new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })),
            datasets: [{
              label: 'Daily accuracy', data: history.map((day) => day.accuracy),
              borderColor: color('--green'), backgroundColor: color('--selection-surface'),
              fill: true, tension: 0.2, spanGaps: false, pointRadius: 4,
            }],
          },
          options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            plugins: {
              legend: { display: false },
              tooltip: { callbacks: {
                label: (context) => `Accuracy: ${context.parsed.y}% · ${history[context.dataIndex].completed} activities`,
              } },
            },
            scales: {
              y: { min: 0, max: 100, ticks: { color: color('--muted'), callback: (value) => `${value}%` }, grid: { color: color('--line') } },
              x: { ticks: { color: color('--muted'), maxTicksLimit: 6 }, grid: { display: false } },
            },
          },
        });
      };
      let chart = render();
      const observer = new MutationObserver(() => { chart.destroy(); chart = render(); });
      observer.observe(root, { attributes: true, attributeFilter: ['data-theme', 'data-font-size', 'data-reading-font'] });
      onCleanup(() => { observer.disconnect(); chart.destroy(); });
    });
  }
}

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
