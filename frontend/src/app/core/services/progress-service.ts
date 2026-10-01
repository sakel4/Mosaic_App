import { Injectable, signal } from '@angular/core';
import { Progress } from '../models/progress.model';
import { Achievement } from '../models/achievement.model';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { defaultProgress } from './dummy_data';

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private readonly currentProgress = signal<Progress>(structuredClone(defaultProgress));
  readonly progress = this.currentProgress.asReadonly();

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.currentProgress.update((progress) => ({
      ...progress,
      exercisesCompleted: progress.exercisesCompleted + 1,
      skills: progress.skills.map((item) =>
        item.name === skill
          ? {
              ...item,
              progress: attempt.correct ? Math.min(100, item.progress + 2) : item.progress,
            }
          : item,
      ),
    }));
  }

  addAchievement(achievement: Achievement): void {
    this.currentProgress.update((progress) => ({
      ...progress,
      achievements: [...progress.achievements, achievement],
    }));
  }
}
