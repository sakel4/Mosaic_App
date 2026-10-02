import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRouteSnapshot, provideRouter, RouterStateSnapshot } from '@angular/router';
import { firstValueFrom, Observable } from 'rxjs';
import { UserService } from './user-service';
import { initialAssessmentGuard } from '../guards/initial-flow-guard';

describe('Onboarding completion API integration', () => {
  let users: UserService;
  let http: HttpTestingController;
  const onboardedUser = {
    id: 'learner', first_name: 'Alex', last_name: 'Smith',
    on_bording_completed: true, assessment_completed: false, profile: null,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
    ] });
    users = TestBed.inject(UserService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('saves the backend onboarding field and allows the initial assessment after reloading', async () => {
    users.save(users.profile(), true).subscribe();
    const save = http.expectOne('/users/me/');
    expect(save.request.method).toBe('PATCH');
    expect(save.request.body.on_bording_completed).toBe(true);
    expect(save.request.body.onboarding_completed).toBeUndefined();
    save.flush(onboardedUser);
    expect(users.onboardingCompleted()).toBe(true);

    const result = firstValueFrom(TestBed.runInInjectionContext(() =>
      initialAssessmentGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot)) as Observable<boolean>);
    http.expectOne('/users/me/').flush(onboardedUser);
    expect(await result).toBe(true);
  });
});
