export interface ExerciseAttempt {
  exerciseId: number;
  answer: string | string[];
  correct: boolean;
  responseTime: number;
  errorType?: string;
  hintsUsed?: number;
}
