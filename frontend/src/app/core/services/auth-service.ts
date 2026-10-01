import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  name: string;
}

interface AuthResponse {
  token: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly TOKEN_KEY = 'access_token';

  private readonly tokenSignal = signal<string | null>(
    localStorage.getItem(this.TOKEN_KEY)
  );

  readonly token = this.tokenSignal.asReadonly();

  readonly isLoggedIn = computed(() => !!this.tokenSignal());

  register(data: RegisterPayload): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/auth/register', data).pipe(
      tap((res) => this.saveToken(res.token)),
    );
  }

  login(data: LoginPayload): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/auth/login', data).pipe(
      tap((res) => this.saveToken(res.token)),
    );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    this.tokenSignal.set(null);
    this.router.navigate(['/auth']);
  }

  private saveToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
    this.tokenSignal.set(token);
  }
}
