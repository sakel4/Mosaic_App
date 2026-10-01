import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { Exercise } from '../../core/models/exercise.model';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { ExerciseService } from '../../core/services/exercise-service';
import { ProgressService } from '../../core/services/progress-service';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-feedback-component/exercise-feedback-component';


@Component({
  imports: [ExcerciseComponent, ExerciseFeedbackComponent, RouterLink],
  selector: 'app-practice',
  styleUrl: './practice.scss',
  templateUrl: './practice.html',
})
export class Practice {
  readonly sessionSize = 6;
  private readonly exercises = inject(ExerciseService);
  private readonly progressService = inject(ProgressService);
  readonly exercise = signal(this.exercises.nextExercise());
  readonly progress = this.progressService.progress;
  readonly feedback = signal(false);
  readonly completedInSet = signal(0);
  readonly setComplete = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);

  onCompleted(attempt: ExerciseAttempt): void {
    this.lastAttempt.set(attempt);
    this.progressService.recordAttempt(attempt, this.exercise().skill);
    this.completedInSet.update((count) => Math.min(this.sessionSize, count + 1));
    this.feedback.set(true);
  }

  continuePractice(): void {
    if (this.completedInSet() === this.sessionSize) {
      this.feedback.set(false);
      this.setComplete.set(true);
      return;
    }
    this.feedback.set(false);
    this.exercise.set(this.exercises.nextExercise());
  }

  startAnotherSet(): void {
    this.completedInSet.set(0);
    this.setComplete.set(false);
    this.feedback.set(false);
    this.lastAttempt.set(null);
    this.exercise.set(this.exercises.nextExercise());
  }
}
