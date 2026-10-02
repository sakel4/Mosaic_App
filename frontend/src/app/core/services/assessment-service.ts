import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { defer, delay, map, Observable, of } from 'rxjs';
import { ProgressService } from './progress-service';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { AssessmentExercise, AssessmentResponse, assessmentExercises } from '../models/assessment.model';
import assessmentFixture from '../data/assessment-12-15.json';

@Injectable({ providedIn: 'root' })
export class AssessmentService {
  private readonly http = inject(HttpClient);
  private readonly progressService = inject(ProgressService);
  private readonly attempts = signal<ExerciseAttempt[]>([]);

  getAssessment(): Observable<AssessmentExercise[]> {
    // A cold stream with a fresh response per subscription, like HttpClient.get().
    // Replace this fixture stream with http.get<AssessmentResponse>(url) when ready.
    return defer(() => of(structuredClone(assessmentFixture) as AssessmentResponse)).pipe(
      delay(400),
      map(assessmentExercises),
    );
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
