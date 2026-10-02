import { inject, Injectable } from '@angular/core';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import data from '../data/IRL_SCENARIO.json'
import { ProgressService } from './progress-service';
import { UserService } from './user-service';
import { RealWorldScenario } from '../models/real-world-scenario.model';


interface RawScenario {
  id: string; title: string; context: string; information: string[];
  question: string; options: string[]; correct_answer: string | string[];
}

@Injectable({ providedIn: 'root' })
export class RealWorldService {
  private readonly progressService = inject(ProgressService);
  private readonly users = inject(UserService);
  private lastId: string | null = null;

  nextScenario(): RealWorldScenario {
    const groups = data.age_groups as Record<string, RawScenario[]>;
    const pool = groups[this.users.profile().ageGroup] ?? groups['under_12'];
    const choices = pool.filter((s) => s.id !== this.lastId);
    const raw = choices[Math.floor(Math.random() * choices.length)] ?? pool[0];
    this.lastId = raw.id;
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
            correctAnswer: Array.isArray(raw.correct_answer) ? raw.correct_answer[0] : raw.correct_answer,
            explanation: ''
        },
      },
    };
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.progressService.recordAttempt(attempt, skill);
  }
}