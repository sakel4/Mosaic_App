import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, CanActivateFn, provideRouter, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { firstValueFrom, Observable, of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { UserService } from '../services/user-service';
import { initialAssessmentGuard, initialOnboardingGuard } from './initial-flow-guard';
import { AssessedGuard } from './assessed-guard';

describe('Initial assessment route guards', () => {
  const users = {
    load: vi.fn(),
    assessmentCompleted: vi.fn(),
    onboardingCompleted: vi.fn(),
  };

  beforeEach(() => {
    users.load.mockReturnValue(of({}));
    TestBed.configureTestingModule({ providers: [
      provideRouter([]),
      { provide: UserService, useValue: users },
    ] });
  });

  async function check(guard: CanActivateFn): Promise<boolean | string> {
    const result = await firstValueFrom(TestBed.runInInjectionContext(() =>
      guard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot)) as Observable<boolean | UrlTree>);
    return result instanceof UrlTree ? TestBed.inject(Router).serializeUrl(result) : result;
  }

  it.each([
    [false, false, '/onboarding', true, '/onboarding'],
    [true, false, true, '/assessment', '/assessment'],
    [true, true, '/dashboard', '/dashboard', true],
    [false, true, '/dashboard', '/dashboard', true],
  ])('routes onboarding=%s and assessment=%s to the correct step', async (
    onboarded, assessed, assessmentResult, onboardingResult, dashboardResult,
  ) => {
    users.onboardingCompleted.mockReturnValue(onboarded);
    users.assessmentCompleted.mockReturnValue(assessed);
    expect(await check(initialAssessmentGuard)).toBe(assessmentResult);
    expect(await check(initialOnboardingGuard)).toBe(onboardingResult);
    expect(await check(AssessedGuard)).toBe(dashboardResult);
  });

  it('redirects to login when the user is unauthorized', async () => {
    users.load.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401 })));
    expect(await check(initialAssessmentGuard)).toBe('/login');
    expect(await check(initialOnboardingGuard)).toBe('/login');
    expect(await check(AssessedGuard)).toBe('/login');
  });

  it('blocks navigation without redirecting when the backend is down', async () => {
    users.load.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 0 })));
    expect(await check(initialAssessmentGuard)).toBe(false);
    expect(await check(initialOnboardingGuard)).toBe(false);
    expect(await check(AssessedGuard)).toBe(false);
  });
});
