import { inject, Injectable } from '@angular/core';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { RealWorldScenario } from '../models/real-world-scenario.model';
import data from '../data/IRL_SCENARIO.json';
import { ProgressService } from './progress-service';
import { UserService } from './user-service';

interface RawScenario {
  id: string;
  title: string;
  context: string;
  information: string[];
  question: string;
  options: string[];
  correct_answer: string | string[];
}

@Injectable({ providedIn: 'root' })
export class RealWorldService {
  private readonly progressService = inject(ProgressService);
  private readonly users = inject(UserService);
  private lastId: string | null = null;

  nextScenario(): RealWorldScenario {
    const groups = data.age_groups as unknown as Record<string, RawScenario[]>;
    const ageGroup = this.users.profile().ageGroup;
    // Backend calls this group "19_plus"; the scenario file calls it "18_plus".
    const key = ageGroup === '19_plus' ? '18_plus' : ageGroup;
    const pool = groups[key] ?? groups['under_12'];
    const choices = pool.length > 1 ? pool.filter((s) => s.id !== this.lastId) : pool;
    const raw = choices[Math.floor(Math.random() * choices.length)];
    this.lastId = raw.id;
    const correct = Array.isArray(raw.correct_answer) ? raw.correct_answer[0] : raw.correct_answer;
    return {
      id: raw.id,
      title: raw.title,
      context: raw.context,
      information: raw.information,
      exercise: {
        id: pool.indexOf(raw) + 1,
        type: 'comprehension',
        skill: 'Everyday reading',
        difficulty: 2,
        content: {
          prompt: raw.question,
          options: raw.options,
          correctAnswer: correct,
          explanation: `Correct: ${correct}.`,
        },
      },
    };
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.progressService.recordAttempt(attempt, skill);
  }
}
