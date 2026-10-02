import { Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { AssessmentExercise } from '../../core/models/assessment.model';
import { DailyRealLife, DailyRealLifeAttempt } from '../../core/models/daily-real-life.model';
import { RealWorldService } from '../../core/services/real-world-service';
import { ProgressService } from '../../core/services/progress-service';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-feedback-component/exercise-feedback-component';

@Component({
  imports: [ExcerciseComponent, ExerciseFeedbackComponent, DatePipe],
  selector: 'app-real-world',
  styleUrl: './real-world.scss',
  templateUrl: './real-world.html',
})
export class RealWorld {
  private readonly realWorld = inject(RealWorldService);
  private readonly progress = inject(ProgressService);
  private readonly destroyRef = inject(DestroyRef);
  readonly daily = signal<DailyRealLife | null>(null);
  readonly active = signal<DailyRealLifeAttempt | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly loadError = signal('');
  readonly saveError = signal('');
  readonly expired = signal(false);
  readonly feedback = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);
  readonly pendingAttempt = signal<ExerciseAttempt | null>(null);
  readonly exercise = computed<AssessmentExercise | null>(() => {
    const active = this.active();
    if (!active) return null;
    return {
      id: active.attempt_id, position: 1, kind: 'comprehension', skill: 'Everyday reading',
      response_type: 'single_choice_set', instruction: 'Read the information, then choose your answer.',
      content_data: { items: [{ id: active.exercise.id, prompt: active.exercise.question,
        options: active.exercise.options.map(text => ({ id: text, text })),
        ...(active.completed_at && active.correct_answer ? { correct_option_id: active.correct_answer } : {}),
      }] },
    };
  });

  constructor() { this.loadDaily(); }

  loadDaily(): void {
    if (this.loading() || this.saving()) return;
    this.loading.set(true);
    this.loadError.set('');
    this.saveError.set('');
    this.expired.set(false);
    this.feedback.set(false);
    this.lastAttempt.set(null);
    this.pendingAttempt.set(null);
    this.active.set(null);
    this.realWorld.getDailyExercises().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: daily => {
        this.daily.set(daily);
        this.active.set(daily.locked ? null : daily.exercises.find(item => !item.completed_at) ?? null);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set('Could not load your daily scenarios. Please try again.');
      },
    });
  }

  onCompleted(attempt: ExerciseAttempt): void {
    const active = this.active();
    if (!active || active.completed_at || this.saving() || this.feedback() || this.pendingAttempt()
      || String(attempt.exerciseId) !== active.attempt_id || typeof attempt.answer !== 'string') return;
    this.pendingAttempt.set(structuredClone(attempt));
    this.saveCompletion();
  }

  saveCompletion(): void {
    const active = this.active();
    const pending = this.pendingAttempt();
    if (!active || active.completed_at || !pending || this.saving() || this.expired()) return;
    this.saving.set(true);
    this.saveError.set('');
    this.realWorld.completeExercise(active.attempt_id, pending.answer as string)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: saved => {
          this.active.set(saved);
          const result = { ...pending, answer: saved.answer ?? pending.answer, correct: saved.correct === true, evaluated: true };
          this.lastAttempt.set(result);
          this.progress.refresh();
          this.daily.update(daily => {
            if (!daily) return daily;
            const exercises = daily.exercises.map(item => item.attempt_id === saved.attempt_id ? saved : item);
            const completed = exercises.filter(item => item.completed_at).length;
            return { ...daily, exercises, completed, remaining: daily.daily_limit - completed,
              locked: completed === daily.daily_limit };
          });
          this.pendingAttempt.set(null);
          this.saving.set(false);
          this.feedback.set(true);
        },
        error: error => {
          this.saving.set(false);
          this.expired.set(error.status === 409);
          this.saveError.set(error.status === 409
            ? "This scenario has expired. Load today's scenarios to continue."
            : 'Could not save your answer. Please try again.');
        },
      });
  }

  tryAnother(): void { this.loadDaily(); }
}
