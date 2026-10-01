import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-component/exercise-component';
import { Exercise } from '../../core/models/exercise.model';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model'
// import { RealWorldService } from '../../core/services/onoma.services';


@Component({
  // imports: [ExcerciseComponent, ExerciseFeedbackComponent],
  imports: [],
  selector: 'app-real-world',
  styleUrl: './real-world.scss',
  templateUrl: './real-world.html',
})
export class RealWorld {
  //  private readonly realWorld = inject(RealWorldService);
  // readonly exercise: Exercise = this.realWorld.nextScenario();
  readonly feedback = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);

  onCompleted(attempt: ExerciseAttempt): void {
    this.lastAttempt.set(attempt);
    // this.realWorld.recordAttempt(attempt, this.exercise.skill);
    this.feedback.set(true);
  }

  tryAnother(): void {
    this.feedback.set(false);
    this.lastAttempt.set(null);
  }
}
