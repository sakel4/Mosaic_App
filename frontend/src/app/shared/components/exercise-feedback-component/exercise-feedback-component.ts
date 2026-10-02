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
    if (exercise.response_type === 'spoken') return {
      correctAnswer: (exercise.content_data.passage_lines ?? exercise.content_data.sections?.flatMap((section) => section.items) ?? []).join(' '),
      explanation: 'Your transcription is compared with the reading text.',
    };
    return {
      correctAnswer: (exercise.content_data.items ?? []).map((item) =>
        item.options?.find((option) => option.id === item.correct_option_id)?.text ?? item.word ?? (item.direction === 'reverse' ? [...(item.sequence ?? [])].reverse() : item.sequence ?? []).join(' '),
      ).join(', '),
      explanation: 'Thank you for completing this activity.',
    };
  });
  readonly continueLabel = input('Continue');
  readonly continued = output<void>();
}

