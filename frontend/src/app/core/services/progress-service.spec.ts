import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ProgressService } from './progress-service';
import { AuthService } from './auth-service';
import { httpInterceptor } from '../interceptors/http-interceptor';
import { tokenInterceptor } from '../interceptors/token-interceptor';
import { environment } from '../../../environments/environment';
import { Progress } from '../models/progress.model';

const url = `${environment.apiUrl}/practice/progress/`;
const saved: Progress = { exercisesCompleted: 12, currentStreak: 3,
  skills: [{ id: 1, name: 'Reading fluency', progress: 72, change: 7, metric: 'score' }],
  achievements: [{ id: 1, title: 'First activity', description: 'Well done', icon: 'star' }],
  history: [{ date: '2026-10-02', completed: 2, accuracy: 50 }] };

describe('ProgressService backend integration', () => {
  let service: ProgressService;
  let http: HttpTestingController;
  const token = signal<string | null>('learner-token');
  beforeEach(() => {
    token.set('learner-token');
    TestBed.configureTestingModule({ providers: [
      provideHttpClient(withInterceptors([httpInterceptor, tokenInterceptor])), provideHttpClientTesting(),
      { provide: AuthService, useValue: { token, logout: vi.fn() } },
    ] });
    service = TestBed.inject(ProgressService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('starts empty and loads authenticated saved statistics', () => {
    expect(service.progress().exercisesCompleted).toBe(0);
    service.refresh();
    expect(service.loading()).toBe(true);
    const request = http.expectOne(url);
    expect(request.request.headers.get('Authorization')).toBe('Bearer learner-token');
    request.flush(saved);
    expect(service.progress()).toEqual(saved);
    expect(service.loading()).toBe(false);
  });

  it('saves practice attempts and reloads authoritative totals', () => {
    service.recordAttempt({ exerciseId: 'exercise-1', answer: 'word', correct: true, responseTime: 500 }, 'reading_fluency');
    const post = http.expectOne(url);
    expect(post.request.method).toBe('POST');
    expect(post.request.body).toEqual({ client_id: expect.any(String), exercise_id: 'exercise-1', skill: 'reading_fluency', correct: true, response_time: 500 });
    post.flush(saved);
    http.expectOne(url).flush(saved);
    expect(service.progress().exercisesCompleted).toBe(12);
  });

  it('keeps failed submissions for retry with the same idempotency key', () => {
    service.recordAttempt({ exerciseId: 'exercise-1', answer: 'word', correct: false, evaluated: false, responseTime: 500 }, 'reading_fluency');
    const failed = http.expectOne(url);
    const payload = failed.request.body;
    expect(payload.correct).toBeNull();
    failed.flush({}, { status: 503, statusText: 'Unavailable' });
    expect(service.error()).toContain('Please try again');
    service.refresh();
    const retry = http.expectOne(url);
    expect(retry.request.body).toEqual(payload);
    retry.flush(saved);
    http.expectOne(url).flush(saved);
    expect(service.error()).toBe('');
  });

  it('clears previous user statistics and pending submissions on account changes', () => {
    service.recordAttempt({ exerciseId: 1, answer: 'word', correct: true, responseTime: 1 }, 'Spelling');
    http.expectOne(url).flush({}, { status: 503, statusText: 'Unavailable' });
    token.set('another-learner-token');
    service.refresh();
    const request = http.expectOne(url);
    expect(request.request.method).toBe('GET');
    expect(service.progress().exercisesCompleted).toBe(0);
    request.flush({ ...saved, exercisesCompleted: 0, skills: [] });
  });
});
