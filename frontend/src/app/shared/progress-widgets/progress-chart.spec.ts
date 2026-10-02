import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import Chart from 'chart.js/auto';
import { ProgressChartComponent } from './progress-widgets';
import { ProgressService } from '../../core/services/progress-service';
import { Progress } from '../../core/models/progress.model';

vi.mock('chart.js/auto', () => ({ default: vi.fn(function () { return { destroy: vi.fn() }; }) }));
const empty: Progress = { exercisesCompleted: 0, currentStreak: 0, skills: [], achievements: [], history: [] };
const days = () => Array.from({ length: 42 }, (_, index) => ({
  date: new Date(Date.UTC(2026, 7, 22 + index)).toISOString().slice(0, 10), completed: 0, accuracy: null as number | null,
}));

describe('Adaptive progress chart', () => {
  beforeEach(() => {
    vi.mocked(Chart).mockClear();
    TestBed.configureTestingModule({ imports: [ProgressChartComponent], providers: [
      { provide: ProgressService, useValue: { progress: signal(empty) } },
    ] });
  });

  it('shows a single centered date and a visible point for one day of activity', () => {
    const history = days();
    history[41] = { ...history[41], completed: 3, accuracy: 0 };
    const fixture = TestBed.createComponent(ProgressChartComponent);
    fixture.componentRef.setInput('data', { ...empty, exercisesCompleted: 3, history });
    fixture.detectChanges();
    expect(fixture.componentInstance.history()).toHaveLength(1);
    expect(fixture.nativeElement.textContent).toContain('TODAY');
    const config = vi.mocked(Chart).mock.calls[0][1] as any;
    expect(config.data.labels).toHaveLength(1);
    expect(config.data.datasets[0].data).toEqual([0]);
    expect(config.options.scales.x.offset).toBe(true);
    expect(config.data.datasets[0].clip).toBe(false);
  });

  it('trims leading inactive days while retaining gaps and the latest day', () => {
    const history = days();
    history[38] = { ...history[38], completed: 1, accuracy: 80 };
    history[41] = { ...history[41], completed: 1, accuracy: 100 };
    const fixture = TestBed.createComponent(ProgressChartComponent);
    fixture.componentRef.setInput('data', { ...empty, exercisesCompleted: 2, history });
    fixture.detectChanges();
    expect(fixture.componentInstance.periodLabel()).toBe('LAST 4 DAYS');
    expect(fixture.componentInstance.history().map(day => day.accuracy)).toEqual([80, null, null, 100]);
    expect(fixture.nativeElement.querySelector('caption').textContent).toContain('last 4 days');
  });

  it('keeps the six-week label for a full activity period', () => {
    const history = days();
    history[0] = { ...history[0], completed: 1, accuracy: 50 };
    const fixture = TestBed.createComponent(ProgressChartComponent);
    fixture.componentRef.setInput('data', { ...empty, exercisesCompleted: 1, history });
    fixture.detectChanges();
    expect(fixture.componentInstance.periodLabel()).toBe('LAST SIX WEEKS');
    expect(fixture.componentInstance.history()).toHaveLength(42);
  });

  it('shows unscored results without an empty chart', () => {
    const history = days();
    history[41].completed = 1;
    const fixture = TestBed.createComponent(ProgressChartComponent);
    fixture.componentRef.setInput('data', { ...empty, exercisesCompleted: 1, history });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('canvas')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Not scored');
    expect(Chart).not.toHaveBeenCalled();
  });

  it('automatically shows hourly buckets with gaps and can switch back to daily', () => {
    const history = days();
    history[41] = { ...history[41], completed: 3, accuracy: 67 };
    const fixture = TestBed.createComponent(ProgressChartComponent);
    fixture.componentRef.setInput('data', { ...empty, exercisesCompleted: 3, history,
      hourlyHistory: [
        { date: history[41].date, hour: 9, completed: 2, accuracy: 100 },
        { date: history[41].date, hour: 11, completed: 1, accuracy: 0 },
      ], timeZone: 'Europe/Athens',
    });
    fixture.detectChanges();
    expect(fixture.componentInstance.isHourly()).toBe(true);
    expect(fixture.componentInstance.chartRows().map(row => row.label)).toEqual(['09:00', '10:00', '11:00']);
    expect(fixture.componentInstance.chartRows().map(row => row.accuracy)).toEqual([100, null, 0]);
    expect(fixture.nativeElement.textContent).toContain('Hourly accuracy');
    fixture.componentInstance.view.set('daily');
    fixture.detectChanges();
    expect(fixture.componentInstance.chartRows()).toHaveLength(1);
    expect(fixture.componentInstance.periodLabel()).toBe('TODAY');
  });

  it('allows choosing a previous day for hourly detail', () => {
    const history = days();
    history[40] = { ...history[40], completed: 1, accuracy: 100 };
    history[41] = { ...history[41], completed: 1, accuracy: 0 };
    const fixture = TestBed.createComponent(ProgressChartComponent);
    fixture.componentRef.setInput('data', { ...empty, exercisesCompleted: 2, history,
      hourlyHistory: [
        { date: history[40].date, hour: 8, completed: 1, accuracy: 100 },
        { date: history[41].date, hour: 12, completed: 1, accuracy: 0 },
      ],
    });
    fixture.componentInstance.view.set('hourly');
    fixture.componentInstance.selectedDate.set(history[40].date);
    fixture.detectChanges();
    expect(fixture.componentInstance.chartRows()[0].label).toBe('08:00');
    expect(fixture.componentInstance.chartRows()[0].accuracy).toBe(100);
  });
});
