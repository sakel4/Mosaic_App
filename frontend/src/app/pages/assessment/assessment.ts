import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ExcerciseComponent } from '../../shared/components/excercise-component/excercise-component';
import { ExerciseFeedbackComponent } from '../../shared/components/excercise-component/excercise-component';
import { Exercise } from '../../core/models/exercise.model';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { AuthService } from '../../core/services/auth-service';
// import { AssessmentService, AuthService } from '../../core/services/onoma.services';
@Component({
  // imports: [ExcerciseComponent, ExerciseFeedbackComponent, RouterLink],
  imports: [RouterLink],
  selector: 'app-assessment',
  styleUrl: './assessment.scss',
  templateUrl: './assessment.html',
})
export class Assessment {
  // private readonly assessmentService = inject(AssessmentService);
  // private readonly auth = inject(AuthService); ( Better use user)
  private readonly router = inject(Router);
  // readonly exercises = this.assessmentService.getAssessment();
  readonly index = signal(0);
  // readonly exercise = computed(() => this.exercises[this.index()]);
  readonly feedback = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);

  onCompleted(attempt: ExerciseAttempt): void {
    this.lastAttempt.set(attempt);
    // this.assessmentService.recordAttempt(attempt, this.exercise().skill);
    // if (this.index() === this.exercises.length - 1) {
    //   this.auth.completeAssessment(); ( user)
    // }
    this.feedback.set(true);
  }

  nextExercise(): void {
    // if (this.index() === this.exercises.length - 1) {
    //   void this.router.navigate(['/profile'], { queryParams: { afterAssessment: 'true' } });
    //   return;
    // }
    this.index.update((value) => value + 1);
    this.feedback.set(false);
  }
}
