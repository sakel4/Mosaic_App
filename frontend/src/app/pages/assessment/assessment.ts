import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ExcerciseComponent} from '../../shared/components/exercise-component/exercise-component';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { AssessmentService } from '../../core/services/assessment-service';
import { UserService } from '../../core/services/user-service';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-feedback-component/exercise-feedback-component';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AssessmentExercise } from '../../core/models/assessment.model';

@Component({
  imports: [ExcerciseComponent, ExerciseFeedbackComponent, RouterLink],
  selector: 'app-assessment',
  styleUrl: './assessment.scss',
  templateUrl: './assessment.html',
})
export class Assessment {
  private readonly assessmentService = inject(AssessmentService);
  private readonly users = inject(UserService);
  private readonly router = inject(Router);
  private readonly loadedExercises = signal<AssessmentExercise[]>([]);
  get exercises(): AssessmentExercise[] { return this.loadedExercises(); }
  readonly estimatedMinutes = this.assessmentService.estimatedMinutes;
  readonly loading = signal(true);
  readonly loadError = signal('');
  readonly index = signal(0);
  readonly exercise = computed(() => this.exercises[this.index()]);
  readonly feedback = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);
  readonly saving = signal(false);
  readonly saveError = signal('');

  constructor() {
    this.assessmentService.getAssessment().pipe(takeUntilDestroyed()).subscribe({
      next: (exercises) => {
        this.loadedExercises.set(exercises);
        this.loading.set(false);
        if (!exercises.length) this.loadError.set('No assessment activities are available.');
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set('Could not load your assessment. Please refresh to try again.');
      },
    });
  }

  onCompleted(attempt: ExerciseAttempt): void {
    if (!this.exercise()) return;
    this.lastAttempt.set({ exerciseId: attempt.exerciseId, answer: '', correct: attempt.correct,
      evaluated: attempt.evaluated, responseTime: attempt.responseTime });
    this.feedback.set(true);
  }

  nextExercise(): void {
    if (!this.feedback() || this.saving()) return;
    if (this.index() === this.exercises.length - 1) {
      this.saving.set(true);
      this.saveError.set('');
      this.users.completeAssessment().subscribe({
        next: () => { this.lastAttempt.set(null); void this.router.navigate(['/dashboard']); },
        error: () => {
          this.saving.set(false);
          this.saveError.set('Could not save your assessment. Please try again.');
        },
      });
      return;
    }
    this.index.update((value) => value + 1);
    this.feedback.set(false);
    this.lastAttempt.set(null);
  }
}
