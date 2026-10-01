import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { ExerciseService } from './exercise-service';
import { ProgressService } from './progress-service';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { Exercise } from '../models/exercise.model';

@Injectable({ providedIn: 'root' })
export class AssessmentService {
  private readonly http = inject(HttpClient);
  private readonly exerciseService = inject(ExerciseService);
  private readonly progressService = inject(ProgressService);
  private readonly attempts = signal<ExerciseAttempt[]>([]);

  getAssessment(): Exercise[] {
    return this.exerciseService.assessmentExercises();
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.progressService.recordAttempt(attempt, skill);
    this.attempts.update((list) => [
      ...list.filter((a) => a.exerciseId !== attempt.exerciseId),
      attempt,
    ]);
  }

  submit(assessmentVersion: string): Observable<unknown> {
    const total = {
      assessment_version: assessmentVersion,
      responses: this.attempts().map((a) => ({
        exercise_id: String(a.exerciseId),
        answers: { answer: a.answer },
      })),
    };
    return this.http.post('/practice/assessment/submit/', total);
  }
}