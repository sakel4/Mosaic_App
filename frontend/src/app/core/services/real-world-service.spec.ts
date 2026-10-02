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
  it('requests a generated real-life set with the user token', () => {
    service.getSet().subscribe();
    const request = http.expectOne(`${environment.apiUrl}/real_life_set/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('Authorization')).toBe('Bearer learner-token');
    request.flush({ id: 'set-1', category: 'Money', age_group: { '12_15': [] } });
  });

  it('sends the per-exercise results to the evaluation endpoint', () => {
    service.evaluate('set-1', { 'set-1_01': true, 'set-1_02': false }).subscribe();
    const request = http.expectOne(`${environment.apiUrl}/real_life_set/evaluate/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('Authorization')).toBe('Bearer learner-token');
    expect(request.request.body).toEqual({ real_life_set_id: 'set-1', answers: { 'set-1_01': true, 'set-1_02': false } });
    request.flush({ id: 'eval-1', correct: 1, total: 2 });
  });
});
