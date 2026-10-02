import { HttpErrorResponse } from '@angular/common/http';
import { Router, UrlTree } from '@angular/router';

// Redirecting on network/server errors loops with guestGuard, so only auth failures redirect.
export function guardErrorResult(err: unknown, router: Router): UrlTree | false {
  return err instanceof HttpErrorResponse && err.status === 401
    ? router.createUrlTree(['/login'])
    : false;
}
