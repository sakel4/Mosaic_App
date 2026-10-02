import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { map, Observable } from 'rxjs';
import { AssessmentExercise, AssessmentResponse, assessmentExercises } from '../models/assessment.model';

export interface CompletedAssessment {
  assessment_id: string | null;
  answers: { exercise_id: string; answers: Record<string, string | string[]> }[];
}

@Injectable({ providedIn: 'root' })
export class AssessmentService {
  private readonly http = inject(HttpClient);

  private assessmentId: string | null = null;
  private readonly result = signal<CompletedAssessment | null>(null);
  readonly completedAssessment = this.result.asReadonly();

  readonly estimatedMinutes = signal(10);

  getAssessment(): Observable<AssessmentExercise[]> {
    return this.http.get<AssessmentResponse>('/assessments/initial/').pipe(
      map((response) => {
        const assessment = Array.isArray(response) ? response[0]
          : 'assessment' in response ? response.assessment : response;
        this.assessmentId = assessment?.id ?? null;
        this.result.set(null);
        this.estimatedMinutes.set(Math.max(1, Math.ceil((assessment?.estimated_duration_seconds ?? 600) / 60)));
        return assessmentExercises(response);
      }),
    );
  }

  finishAssessment(attempts: ExerciseAttempt[]): void {
    this.result.set({
      assessment_id: this.assessmentId,
      answers: attempts.map((attempt) => ({
        exercise_id: String(attempt.exerciseId),
        answers: structuredClone(attempt.itemAnswers ?? { answer: attempt.answer }),
      })),
    });
    console.log('Completed assessment:', this.completedAssessment());
  }
}
