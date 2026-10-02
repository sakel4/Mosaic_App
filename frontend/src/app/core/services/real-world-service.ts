import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DailyRealLife, DailyRealLifeAttempt } from '../models/daily-real-life.model';

@Injectable({ providedIn: 'root' })
export class RealWorldService {
  private readonly http = inject(HttpClient);

  getDailyExercises(): Observable<DailyRealLife> {
    return this.http.get<DailyRealLife>('/assessments/real_life/daily/');
  }

  completeExercise(attemptId: string, answer: string): Observable<DailyRealLifeAttempt> {
    return this.http.post<DailyRealLifeAttempt>(
      `/assessments/real_life/${encodeURIComponent(attemptId)}/complete/`, { answer },
    );
  }
}
