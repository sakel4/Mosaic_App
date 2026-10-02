export interface RealLifeExercise {
  id: string;
  title: string;
  context: string;
  information: string[];
  question: string;
  options: string[];
  correct_answer: string[];
}

export interface RealLifeEvaluation {
  id: string;
  correct: number;
  total: number;
}

export interface RealLifeSet {
  id: string;
  category: string;
  age_group: Record<string, RealLifeExercise[]>;
}
