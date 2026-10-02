import { Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { AssessmentExercise } from '../../core/models/assessment.model';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { ExerciseService } from '../../core/services/exercise-service';
import { ProgressService } from '../../core/services/progress-service';
import { UserService } from '../../core/services/user-service';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-feedback-component/exercise-feedback-component';


@Component({
  imports: [ExcerciseComponent, ExerciseFeedbackComponent, RouterLink],
  selector: 'app-practice',
  styleUrl: './practice.scss',
  templateUrl: './practice.html',
})
export class Practice {
  private readonly destroyRef = inject(DestroyRef);
  private readonly activities = signal<AssessmentExercise[]>([]);
  readonly sessionSize = computed(() => this.activities().length);
  private readonly exercises = inject(ExerciseService);
  private readonly progressService = inject(ProgressService);
  private readonly users = inject(UserService);
  readonly exercise = signal<AssessmentExercise | null>(null);
  readonly skillLabel = computed(() => {
    const label = (this.exercise()?.skill ?? '').replace(/\*/g, '').replace(/_/g, ' ').trim();
    return label.charAt(0).toUpperCase() + label.slice(1);
  });
  readonly showDifficulty = computed(() => {
    const ageGroup = this.users.profile().ageGroup;
    return !!ageGroup && ageGroup !== 'under_12';
  });
  readonly loading = signal(false);
  readonly loadError = signal('');
  readonly progress = this.progressService.progress;
  readonly feedback = signal(false);
  readonly completedInSet = signal(0);
  readonly setComplete = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);

  constructor() { this.loadPractice(); }

  loadPractice(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.loadError.set('');
    this.exercise.set(null);
    this.exercises.getPracticeExercises().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (activities) => {
        this.activities.set(activities);
        this.exercise.set(activities[0] ?? null);
        this.loading.set(false);
        if (!activities.length) this.loadError.set('No practice activities are available. Please try again.');
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set('Could not load your practice activities. Please try again.');
      },
    });
  }

  onCompleted(attempt: ExerciseAttempt): void {
    const exercise = this.exercise();
    if (!exercise || this.feedback() || this.setComplete()) return;
    this.lastAttempt.set(attempt);
    this.progressService.recordAttempt(attempt, exercise.skill);
    this.completedInSet.update((count) => Math.min(this.sessionSize(), count + 1));
    this.feedback.set(true);
  }

  continuePractice(): void {
    if (!this.feedback()) return;
    this.lastAttempt.set(null);
    if (this.completedInSet() === this.sessionSize()) {
      this.feedback.set(false);
      this.setComplete.set(true);
      return;
    }
    this.feedback.set(false);
    this.exercise.set(this.activities()[this.completedInSet()] ?? null);
  }

  startAnotherSet(): void {
    this.completedInSet.set(0);
    this.setComplete.set(false);
    this.feedback.set(false);
    this.lastAttempt.set(null);
    this.loadPractice();
  }
}
