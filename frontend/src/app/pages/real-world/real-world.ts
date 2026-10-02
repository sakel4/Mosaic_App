import { Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { AssessmentExercise } from '../../core/models/assessment.model';
import { RealLifeEvaluation, RealLifeExercise, RealLifeSet } from '../../core/models/real-life-set.model';
import { RealWorldService } from '../../core/services/real-world-service';
import { ProgressService } from '../../core/services/progress-service';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-feedback-component/exercise-feedback-component';

const COMPLETED_AT_KEY = 'mosaic.realWorld.completedAt';
const COOLDOWN_MS = 24 * 60 * 60 * 1000;

@Component({
  imports: [ExcerciseComponent, ExerciseFeedbackComponent],
  selector: 'app-real-world',
  styleUrl: './real-world.scss',
  templateUrl: './real-world.html',
})
export class RealWorld {
  private readonly realWorld = inject(RealWorldService);
  private readonly progress = inject(ProgressService);
  private readonly destroyRef = inject(DestroyRef);
  readonly set = signal<RealLifeSet | null>(null);
  readonly index = signal(0);
  readonly results = signal<Record<string, boolean>>({});
  readonly feedback = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);
  readonly evaluating = signal(false);
  readonly evaluateError = signal('');
  readonly evaluation = signal<RealLifeEvaluation | null>(null);
  readonly loading = signal(false);
  readonly loadError = signal('');
  readonly hoursLeft = signal(0);
  readonly locked = computed(() => this.hoursLeft() > 0);
  readonly exercises = computed<RealLifeExercise[]>(() => Object.values(this.set()?.age_group ?? {})[0] ?? []);
  readonly active = computed(() => this.exercises()[this.index()] ?? null);
  readonly finished = computed(() => this.exercises().length > 0 && this.index() >= this.exercises().length);
  readonly exercise = computed<AssessmentExercise | null>(() => {
    const active = this.active();
    if (!active) return null;
    return {
      id: active.id, position: this.index() + 1, kind: 'comprehension', skill: 'Everyday reading',
      response_type: 'single_choice_set', instruction: 'Read the information, then choose your answer.',
      content_data: { items: [{ id: active.id, prompt: active.question,
        options: active.options.map(text => ({ id: text, text })),
        correct_option_id: active.correct_answer[0] }] },
    };
  });

  constructor() { this.loadSet(); }

  private remainingMs(): number {
    const completedAt = Number(localStorage.getItem(COMPLETED_AT_KEY));
    return completedAt ? Math.max(0, completedAt + COOLDOWN_MS - Date.now()) : 0;
  }

  loadSet(): void {
    if (this.loading()) return;
    const remaining = this.remainingMs();
    this.hoursLeft.set(Math.ceil(remaining / 3_600_000));
    if (remaining > 0) return;
    this.loading.set(true);
    this.loadError.set('');
    this.set.set(null);
    this.index.set(0);
    this.results.set({});
    this.feedback.set(false);
    this.lastAttempt.set(null);
    this.evaluating.set(false);
    this.evaluateError.set('');
    this.evaluation.set(null);
    this.realWorld.getSet().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: set => {
        this.set.set(set);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set('Could not load your real-life scenarios. Please try again.');
      },
    });
  }

  onCompleted(attempt: ExerciseAttempt): void {
    const active = this.active();
    if (!active || this.feedback() || String(attempt.exerciseId) !== active.id || typeof attempt.answer !== 'string') return;
    const correct = active.correct_answer.includes(attempt.answer);
    this.results.update(results => ({ ...results, [active.id]: correct }));
    const scored = { ...attempt, correct, evaluated: true };
    this.lastAttempt.set(scored);
    this.progress.recordAttempt(scored, 'Everyday reading');
    this.feedback.set(true);
  }

  next(): void {
    this.feedback.set(false);
    this.lastAttempt.set(null);
    this.index.update(index => index + 1);
    if (this.finished()) {
      localStorage.setItem(COMPLETED_AT_KEY, String(Date.now()));
      this.submitEvaluation();
    }
  }

  submitEvaluation(): void {
    const set = this.set();
    if (!set || this.evaluating() || this.evaluation()) return;
    this.evaluating.set(true);
    this.evaluateError.set('');
    this.realWorld.evaluate(set.id, this.results()).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: evaluation => {
        this.evaluation.set(evaluation);
        this.evaluating.set(false);
      },
      error: () => {
        this.evaluating.set(false);
        this.evaluateError.set('Could not save your results. Please try again.');
      },
    });
  }
}
