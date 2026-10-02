import { Component, inject, signal } from '@angular/core';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { ExerciseAttempt } from '../../core/models/exercise-attempt.model';
import { RealWorldService } from '../../core/services/real-world-service';
import { ExerciseFeedbackComponent } from '../../shared/components/exercise-feedback-component/exercise-feedback-component';

@Component({
  imports: [ExcerciseComponent, ExerciseFeedbackComponent],
  selector: 'app-real-world',
  styleUrl: './real-world.scss',
  templateUrl: './real-world.html',
})
export class RealWorld {
  private readonly realWorld = inject(RealWorldService);
  scenario = this.realWorld.nextScenario();
  readonly feedback = signal(false);
  readonly lastAttempt = signal<ExerciseAttempt | null>(null);

  onCompleted(attempt: ExerciseAttempt): void {
    this.lastAttempt.set(attempt);
    this.realWorld.recordAttempt(attempt, this.scenario.exercise.skill);
    this.feedback.set(true);
  }

  tryAnother(): void {
    this.scenario = this.realWorld.nextScenario();
    this.feedback.set(false);
    this.lastAttempt.set(null);
  }
}
