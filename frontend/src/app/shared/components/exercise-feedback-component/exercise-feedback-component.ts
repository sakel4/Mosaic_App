import { Component, computed, input, output } from '@angular/core';
import { ExerciseAttempt } from '../../../core/models/exercise-attempt.model';
import { Exercise } from '../../../core/models/exercise.model';
import { AssessmentExercise } from '../../../core/models/assessment.model';

@Component({
  imports: [],
  selector: 'app-exercise-feedback-component',
  styleUrl: './exercise-feedback-component.scss',
  templateUrl: './exercise-feedback-component.html',
})

export class ExerciseFeedbackComponent {
  readonly attempt = input.required<ExerciseAttempt>();
  readonly exercise = input.required<Exercise | AssessmentExercise>();
  readonly content = computed(() => {
    const exercise = this.exercise();
    if ('content' in exercise) return exercise.content;
    return {
      correctAnswer: exercise.content_data.items.map((item) =>
        item.options.find((option) => option.id === item.correct_option_id)?.text ?? '',
      ).join(', '),
      explanation: 'Each answer is what remains after removing the first sound.',
    };
  });
  readonly continueLabel = input('Continue');
  readonly continued = output<void>();
}

