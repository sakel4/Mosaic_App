import { inject, Injectable } from '@angular/core';
import { Exercise } from '../models/exercise.model';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { ExerciseService } from './exercise-service';
import { ProgressService } from './progress-service';

@Injectable({ providedIn: 'root' })
export class RealWorldService {
  private readonly exerciseService = inject(ExerciseService);
  private readonly progressService = inject(ProgressService);

  nextScenario(): Exercise {
    return this.exerciseService.realWorldExercise();
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.progressService.recordAttempt(attempt, skill);
  }
}
