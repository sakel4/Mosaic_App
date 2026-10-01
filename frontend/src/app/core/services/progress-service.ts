import { Injectable, signal } from '@angular/core';
import { Progress } from '../models/progress.model';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { createProgressPreview } from './progress-preview';

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private readonly currentProgress = signal<Progress>(createProgressPreview());
  readonly progress = this.currentProgress.asReadonly();
  private readonly skillResults = new Map(
    this.progress().skills.map((skill) => [skill.name, { completed: 100, correct: skill.progress }]),
  );

  // Keep the demo interactive until the progress endpoint is available.
  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    const results = this.skillResults.get(skill) ?? { completed: 0, correct: 0 };
    results.completed++;
    results.correct += attempt.correct ? 1 : 0;
    this.skillResults.set(skill, results);
    const skillAccuracy = Math.round(results.correct / results.completed * 100);
    this.currentProgress.update((progress) => {
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      const history = [...(progress.history ?? [])];
      const index = history.findIndex((day) => day.date === today);
      const previous = index >= 0 ? history[index] : { date: today, completed: 0, accuracy: null };
      const completed = previous.completed + 1;
      const accuracy = Math.round(((previous.accuracy ?? 0) * previous.completed + (attempt.correct ? 100 : 0)) / completed);
      const day = { date: today, completed, accuracy };
      if (index >= 0) history[index] = day;
      else history.push(day);
      const skills = progress.skills.map((item) => item.name === skill
        ? { ...item, progress: skillAccuracy, change: skillAccuracy - item.progress } : item);
      if (!skills.some((item) => item.name === skill)) {
        skills.push({ id: Math.max(0, ...skills.map((item) => item.id)) + 1, name: skill, progress: attempt.correct ? 100 : 0, change: 0 });
      }
      return { ...progress, exercisesCompleted: progress.exercisesCompleted + 1, skills, history: history.slice(-42) };
    });
  }
}
