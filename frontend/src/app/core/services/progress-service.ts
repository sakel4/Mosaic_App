import { DestroyRef, inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { concatMap, concatWith, EMPTY, finalize, from, ignoreElements, tap } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Progress } from '../models/progress.model';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { AuthService } from './auth-service';

const emptyProgress = (): Progress => ({ exercisesCompleted: 0, currentStreak: 0, skills: [], achievements: [], history: [] });
interface ProgressSubmission {
  client_id: string;
  exercise_id: string;
  skill: string;
  correct: boolean | null;
  response_time: number;
}

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly currentProgress = signal<Progress>(emptyProgress());
  readonly progress = this.currentProgress.asReadonly();
  readonly loading = signal(false);
  readonly error = signal('');
  private token: string | null | undefined;
  private readonly pending = new Map<string, ProgressSubmission>();

  private checkUser(): void {
    if (this.token !== this.auth.token()) {
      this.token = this.auth.token();
      this.pending.clear();
      this.currentProgress.set(emptyProgress());
    }
  }

  refresh(): void {
    this.checkUser();
    if (this.loading()) return;
    const token = this.token;
    this.loading.set(true);
    this.error.set('');
    from([...this.pending.values()]).pipe(
      concatMap(submission => this.auth.token() !== token ? EMPTY : this.http.post<Progress>('/practice/progress/', submission).pipe(
        tap(() => this.pending.delete(submission.client_id)),
      )),
      ignoreElements(),
      concatWith(this.http.get<Progress>('/practice/progress/')),
      takeUntilDestroyed(this.destroyRef),
      finalize(() => {
        this.loading.set(false);
        if (!this.destroyRef.destroyed && (this.auth.token() !== token || (!this.error() && this.pending.size))) this.refresh();
      }),
    ).subscribe({
      next: progress => { if (this.auth.token() === token) this.currentProgress.set(progress); },
      error: () => { if (this.auth.token() === token) this.error.set('Could not load or save your progress. Please try again.'); },
    });
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.checkUser();
    const clientId = crypto.randomUUID();
    this.pending.set(clientId, {
      client_id: clientId, exercise_id: String(attempt.exerciseId), skill,
      correct: attempt.evaluated === false ? null : attempt.correct,
      response_time: Math.max(0, Math.min(2147483647, Math.round(attempt.responseTime))),
    });
    this.refresh();
  }
}
