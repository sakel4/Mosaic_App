import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RealWorldService } from './real-world-service';
import { AuthService } from './auth-service';
import { httpInterceptor } from '../interceptors/http-interceptor';
import { tokenInterceptor } from '../interceptors/token-interceptor';
import { environment } from '../../../environments/environment';

describe('RealWorldService authenticated requests', () => {
  let http: HttpTestingController;
  let service: RealWorldService;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      provideHttpClient(withInterceptors([httpInterceptor, tokenInterceptor])), provideHttpClientTesting(),
      { provide: AuthService, useValue: { token: () => 'learner-token', logout: vi.fn() } },
    ] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(RealWorldService);
  });
  afterEach(() => http.verify());
  it('fetches the current user daily status and sends chosen answers to the API', () => {
    service.getDailyExercises().subscribe();
    const daily = http.expectOne(`${environment.apiUrl}/assessments/real_life/daily/`);
    expect(daily.request.method).toBe('GET');
    expect(daily.request.headers.get('Authorization')).toBe('Bearer learner-token');
    daily.flush({ exercises: [] });
    service.completeExercise('attempt-1', 'Get ready to leave').subscribe();
    const complete = http.expectOne(`${environment.apiUrl}/assessments/real_life/attempt-1/complete/`);
    expect(complete.request.headers.get('Authorization')).toBe('Bearer learner-token');
    expect(complete.request.method).toBe('POST');
    expect(complete.request.body).toEqual({ answer: 'Get ready to leave' });
    complete.flush({ completed_at: '2026-10-02T10:00:00Z', correct: true });
  });
});
