import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { UserService } from '../services/user-service';

export const OnboardedGuard: CanActivateFn = () => {
    const users = inject(UserService);
    const router = inject(Router);

    return users.load().pipe(
        map(() => users.onboardingCompleted() ? true : router.createUrlTree(['/onboarding'])),
        catchError(() => of(router.createUrlTree(['/login']))),
    );
};