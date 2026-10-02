export interface DailyRealLifeAttempt {
  attempt_id: string;
  exercise: {
    id: string;
    title: string;
    context: string;
    information: string[];
    question: string;
    options: string[];
  };
  completed_at: string | null;
  answer: string | null;
  correct: boolean | null;
  correct_answer: string | null;
}

export interface DailyRealLife {
  date: string;
  daily_limit: number;
  completed: number;
  remaining: number;
  locked: boolean;
  next_available_at: string;
  exercises: DailyRealLifeAttempt[];
}
