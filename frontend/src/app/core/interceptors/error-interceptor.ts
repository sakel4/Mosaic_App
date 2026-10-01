import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { catchError, throwError } from 'rxjs';

function messageFor(err: HttpErrorResponse): string {
  if (err.status === 0) {
    return 'Cannot reach the server. Check your connection.';
  }

  const detail = err.error?.detail;

  return typeof detail === 'string' ? detail : 'Request failed. Please try again.';
}

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const snackBar = inject(MatSnackBar);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse) {
        snackBar.open(
          messageFor(err),
          'Dismiss',
          { duration: 5000 },
        );
      }

      return throwError(() => err);
    }),
  );
};
