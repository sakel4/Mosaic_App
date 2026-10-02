import { Component, input, signal } from '@angular/core';
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
  readonly view = signal<'auto' | 'daily' | 'hourly'>('auto');
  readonly selectedDate = signal('');
  readonly hourlyDates = computed(() => [...new Set((this.progress().hourlyHistory ?? []).map(row => row.date))].sort());
  readonly hourlyDate = computed(() => this.hourlyDates().includes(this.selectedDate()) ? this.selectedDate() : this.hourlyDates().at(-1) ?? '');
  readonly isHourly = computed(() => this.hourlyDates().length > 0 && (this.view() === 'hourly'
    || (this.view() === 'auto' && this.history().filter(day => day.completed > 0).length === 1)));
  readonly history = computed(() => {
    const history = (this.progress().history ?? []).slice(-42);
    const firstActivity = history.findIndex(day => day.completed > 0);
    return firstActivity < 0 ? [] : history.slice(firstActivity);
  });
  readonly periodLabel = computed(() => {
    if (this.isHourly()) return `${this.hourlyDate()} BY HOUR`;
    const days = this.history().length;
    return days === 1 ? 'TODAY' : days >= 42 ? 'LAST SIX WEEKS' : days ? `LAST ${days} DAYS` : 'RECENT PRACTICE';
  });
  readonly chartRows = computed(() => {
    if (!this.isHourly()) return this.history().map(day => ({ ...day,
      label: new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), tableLabel: day.date,
    }));
    const rows = (this.progress().hourlyHistory ?? []).filter(row => row.date === this.hourlyDate()).sort((a, b) => a.hour - b.hour);
    if (!rows.length) return [];
    return Array.from({ length: rows.at(-1)!.hour - rows[0].hour + 1 }, (_, index) => {
      const hour = rows[0].hour + index;
      const row = rows.find(entry => entry.hour === hour);
      const label = `${String(hour).padStart(2, '0')}:00`;
      return { completed: row?.completed ?? 0, accuracy: row?.accuracy ?? null, label, tableLabel: label };
    });
  });
  readonly hasAccuracy = computed(() => this.chartRows().some(day => day.accuracy !== null));
  readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('chart');

  constructor() {
    effect((onCleanup) => {
      const canvas = this.canvas()?.nativeElement;
      const history = this.chartRows();
      const accuracyLabel = this.isHourly() ? 'Hourly accuracy' : 'Daily accuracy';
      if (!canvas || !this.hasAccuracy()) return;
      const root = document.documentElement;
      const render = () => {
        const style = getComputedStyle(root);
        const color = (name: string) => style.getPropertyValue(name).trim();
        return new Chart(canvas, {
          type: 'line',
          data: {
            labels: history.map(day => day.label),
            datasets: [{
              label: accuracyLabel, data: history.map((day) => day.accuracy),
              borderColor: color('--green'), backgroundColor: color('--selection-surface'),
              fill: true, tension: 0.2, spanGaps: false, pointRadius: history.length === 1 ? 6 : 4,
              pointHoverRadius: 7, clip: false,
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
              x: { offset: true, ticks: { color: color('--muted'), maxTicksLimit: 6 }, grid: { display: false } },
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
