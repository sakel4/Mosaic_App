import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RealLifeEvaluation, RealLifeSet } from '../models/real-life-set.model';

@Injectable({ providedIn: 'root' })
export class RealWorldService {
  private readonly http = inject(HttpClient);

  // Each call generates and stores a new set on the backend.
  getSet(): Observable<RealLifeSet> {
    return this.http.post<RealLifeSet>('/real_life_set/', {});
  }

  // answers maps each exercise id to whether the learner answered correctly.
  evaluate(setId: string, answers: Record<string, boolean>): Observable<RealLifeEvaluation> {
    return this.http.post<RealLifeEvaluation>('/real_life_set/evaluate/', {
      real_life_set_id: setId,
      answers,
    });
  }
}
