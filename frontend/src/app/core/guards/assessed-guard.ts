import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { UserService } from '../services/user-service';
import { guardErrorResult } from './guard-error';

export const AssessedGuard: CanActivateFn = () => {
  const users = inject(UserService);
  const router = inject(Router);

  return users.load().pipe(
    map(() => {
      if (users.assessmentCompleted()) return true;
      if (!users.onboardingCompleted()) return router.createUrlTree(['/onboarding']);
      return router.createUrlTree(['/assessment']);
    }),
    catchError((err) => of(guardErrorResult(err, router))),
  );
};
