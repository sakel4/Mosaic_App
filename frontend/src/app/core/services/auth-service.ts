import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { TOKEN_KEY } from '../token-interceptor';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  name: string;
}



@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  private tokenSignal = signal<string | null>(localStorage.getItem(TOKEN_KEY));

  readonly token = this.tokenSignal.asReadonly();
  readonly isLoggedIn = computed(() => !!this.tokenSignal());

  register(data: RegisterPayload): Observable<any> {
    return this.http.post<any>('/auth/register', data).pipe(
      tap((res) => this.saveToken(res.token)),
    );
  }

  login(data: LoginPayload): Observable<any> {
    return this.http.post<any>('/auth/login', data).pipe(
      tap((res) => this.saveToken(res.token)),
    );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.tokenSignal.set(null);
    this.router.navigate(['/auth']);
  }

  private saveToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    this.tokenSignal.set(token);
  }
}