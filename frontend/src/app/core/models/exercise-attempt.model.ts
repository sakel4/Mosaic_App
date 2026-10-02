export interface ExerciseAttempt {
  exerciseId: string | number;
  answer: string | string[];
  correct: boolean;
  evaluated?: boolean;
  responseTime: number;
  errorType?: string;
  hintsUsed?: number;
  itemAnswers?: Record<string, string | string[]>;
}
