import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { map, Observable } from 'rxjs';
import { AssessmentExercise, AssessmentResponse, assessmentExercises } from '../models/assessment.model';

@Injectable({ providedIn: 'root' })
export class AssessmentService {
  private readonly http = inject(HttpClient);

  readonly estimatedMinutes = signal(10);

  getAssessment(): Observable<AssessmentExercise[]> {
    return this.http.get<AssessmentResponse>('/assessments/initial/').pipe(
      map((response) => {
        const assessment = Array.isArray(response) ? response[0]
          : 'assessment' in response ? response.assessment : response;
        this.estimatedMinutes.set(Math.max(1, Math.ceil((assessment?.estimated_duration_seconds ?? 600) / 60)));
        return assessmentExercises(response);
      }),
    );
  }

}
