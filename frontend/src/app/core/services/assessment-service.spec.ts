import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';
import { AssessmentService } from './assessment-service';
import { AuthService } from './auth-service';
import { httpInterceptor } from '../interceptors/http-interceptor';
import { tokenInterceptor } from '../interceptors/token-interceptor';
import { environment } from '../../../environments/environment';
import assessmentFixture from '../data/assessment-12-15.json';
import suppliedFixture from '../data/assessment-under-12.json';

describe('AssessmentService HTTP integration', () => {
  let http: HttpTestingController;
  let service: AssessmentService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      provideHttpClient(withInterceptors([httpInterceptor, tokenInterceptor])),
      provideHttpClientTesting(),
      { provide: AuthService, useValue: { token: () => 'test-user-token', logout: vi.fn() } },
    ] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(AssessmentService);
  });

  afterEach(() => http.verify());

  it('loads assessment using the current user Bearer token and maps the response', () => {
    const received = vi.fn();
    service.getAssessment().subscribe(received);
    const request = http.expectOne(`${environment.apiUrl}/assessments/initial/`);
    expect(request.request.method).toBe('GET');
    expect(request.request.headers.get('Authorization')).toBe('Bearer test-user-token');
    expect(request.request.params.keys()).toHaveLength(0);
    request.flush(assessmentFixture);
    expect(received).toHaveBeenCalledWith(expect.arrayContaining([
      expect.objectContaining({ position: 1, language: 'en', skill: 'phonological_awareness' }),
    ]));
    expect(received.mock.calls[0][0]).toHaveLength(8);
  });

  it('accepts the supplied array and preserves UUIDs and all response types', () => {
    const received = vi.fn();
    service.getAssessment().subscribe(received);
    http.expectOne(`${environment.apiUrl}/assessments/initial/`).flush(suppliedFixture);
    const activities = received.mock.calls[0][0];
    expect(activities).toHaveLength(7);
    expect(activities[0]).toMatchObject({ id: suppliedFixture[0].excercises[0].id, difficulty: 2, language: 'en' });
    expect(activities.map((activity: { response_type: string }) => activity.response_type))
      .toEqual(['single_choice_set', 'single_choice_set', 'spoken', 'spoken', 'spelling', 'single_choice_set', 'sequence']);
  });

  it('wraps each correctness result in an answer object', () => {
    service.getAssessment().subscribe();
    http.expectOne(`${environment.apiUrl}/assessments/initial/`).flush(suppliedFixture);
    expect(service.completedAssessment()).toBeNull();
    service.finishAssessment([
      { exerciseId: 'choice', answer: '1', itemAnswers: { a: '1' }, correct: true, responseTime: 1 },
      { exerciseId: 'spoken', answer: 'Maya found a box', correct: true, responseTime: 1 },
      { exerciseId: 'sequence', answer: '7 1 4', itemAnswers: { b: ['7', '1', '4'] }, correct: false, responseTime: 1 },
    ]).subscribe();
    expect(service.completedAssessment()).toEqual({
      assessment_id: suppliedFixture[0].id,
      is_initial: true,
      answers: {
        choice: { answer: true },
        spoken: { answer: true },
        sequence: { answer: false },
      },
    });
    const evaluation = http.expectOne(`${environment.apiUrl}/assessments/evaluate/`);
    expect(evaluation.request.method).toBe('POST');
    expect(evaluation.request.headers.get('Authorization')).toBe('Bearer test-user-token');
    expect(evaluation.request.body).toEqual(service.completedAssessment());
    evaluation.flush({ id: 'evaluation-id' });
    service.getAssessment().subscribe();
    http.expectOne(`${environment.apiUrl}/assessments/initial/`).flush(suppliedFixture);
    expect(service.completedAssessment()).toBeNull();
  });

  it('passes HTTP failures to the subscriber', () => {
    const failed = vi.fn();
    service.getAssessment().subscribe({ error: failed });
    http.expectOne(`${environment.apiUrl}/assessments/initial/`).flush(
      { detail: 'Unavailable' }, { status: 503, statusText: 'Service Unavailable' },
    );
    expect(failed).toHaveBeenCalledWith(expect.objectContaining({ status: 503 }));
  });
});
