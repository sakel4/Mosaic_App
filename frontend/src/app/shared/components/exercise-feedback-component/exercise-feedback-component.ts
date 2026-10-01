import { Component, input, output } from '@angular/core';
import { ExerciseAttempt } from '../../../core/models/exercise-attempt.model';
import { Exercise } from '../../../core/models/exercise.model';

@Component({
  imports: [],
  selector: 'app-exercise-feedback-component',
  styleUrl: './exercise-feedback-component.scss',
  templateUrl: './exercise-feedback-component.html',
})

export class ExerciseFeedbackComponent {
  readonly attempt = input.required<ExerciseAttempt>();
  readonly exercise = input.required<Exercise>();
  readonly continueLabel = input('Continue');
  readonly continued = output<void>();
}

