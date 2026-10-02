import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { UserService } from '../services/user-service';
import { guardErrorResult } from './guard-error';

export const initialAssessmentGuard: CanActivateFn = () => {
  const users = inject(UserService);
  const router = inject(Router);

  return users.load().pipe(
    map(() => {
      if (users.assessmentCompleted()) return router.createUrlTree(['/dashboard']);
      return users.onboardingCompleted() ? true : router.createUrlTree(['/onboarding']);
    }),
    catchError((err) => of(guardErrorResult(err, router))),
  );
};

export const initialOnboardingGuard: CanActivateFn = () => {
  const users = inject(UserService);
  const router = inject(Router);

  return users.load().pipe(
    map(() => {
      if (users.assessmentCompleted()) return router.createUrlTree(['/dashboard']);
      return users.onboardingCompleted() ? router.createUrlTree(['/assessment']) : true;
    }),
    catchError((err) => of(guardErrorResult(err, router))),
  );
};
