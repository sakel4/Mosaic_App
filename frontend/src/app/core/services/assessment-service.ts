import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { map, Observable } from 'rxjs';
import { AssessmentExercise, AssessmentResponse, assessmentExercises } from '../models/assessment.model';

export interface CompletedAssessment {
  assessment_id: string | null;
  is_initial: boolean;
  answers: Record<string, { answer: boolean }>[];
}
@Injectable({ providedIn: 'root' })
export class AssessmentService {
  private readonly http = inject(HttpClient);

  private assessmentId: string | null = null;
  private readonly result = signal<CompletedAssessment | null>(null);
  readonly completedAssessment = this.result.asReadonly();

  readonly estimatedMinutes = signal(10);

  private exercises: AssessmentExercise[] = [];

  getAssessment(): Observable<AssessmentExercise[]> {
    return this.http.get<AssessmentResponse>('/assessments/initial/').pipe(
      map((response) => {
        const assessment = Array.isArray(response) ? response[0]
          : 'assessment' in response ? response.assessment : response;
        this.assessmentId = assessment?.id ?? null;
        this.result.set(null);
        this.estimatedMinutes.set(Math.max(1, Math.ceil((assessment?.estimated_duration_seconds ?? 600) / 60)));
        this.exercises = assessmentExercises(response);
        return this.exercises;
      }),
    );
  }
  finishAssessment(attempts: ExerciseAttempt[]): void {
    this.result.set({
      assessment_id: this.assessmentId,
      is_initial: true,
      answers: attempts.map((attempt) => {
        const exercise = this.exercises.find((e) => String(e.id ?? e.position) === String(attempt.exerciseId));
        const itemId = exercise?.content_data.items?.[0]?.id;
        const key = itemId ? `${attempt.exerciseId}_${itemId}` : String(attempt.exerciseId);
        return { [key]: { answer: attempt.correct } };
      }),
    });
    console.log('Completed assessment:', this.completedAssessment());
  }
}
