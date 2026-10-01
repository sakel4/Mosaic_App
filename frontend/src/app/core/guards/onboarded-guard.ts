import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { UserService } from '../services/user-service';

export const AssessedGuard: CanActivateFn = () => {
    const users = inject(UserService);
    const router = inject(Router);

    return users.load().pipe(
        map(() => users.onboardingCompleted() ? true : router.createUrlTree(['/assessment'])),
        catchError(() => of(router.createUrlTree(['/assessment']))),
    );
};