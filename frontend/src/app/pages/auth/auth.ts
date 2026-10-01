import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/services/auth-service';

@Component({
  imports: [ReactiveFormsModule, RouterLink],
  selector: 'app-auth',
  styleUrl: './auth.scss',
  templateUrl: './auth.html',
})
export class Auth {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    name: ['', this.isRegister ? Validators.required : []],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  get isRegister(): boolean {
    return this.route.snapshot.data['mode'] === 'register';
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (
      this.form.controls.email.invalid ||
      this.form.controls.password.invalid ||
      (this.isRegister && this.form.controls.name.invalid)
    ) {
      return;
    }

    const { name, email, password } = this.form.getRawValue();
    this.loading.set(true);
    this.errorMessage.set(null);

    const request$ = this.isRegister
      ? this.auth.register({ name, email, password })
      : this.auth.login({ email, password });

    request$.subscribe({
      next: () => void this.router.navigate(['/dashboard']),
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        this.errorMessage.set(err.error?.message ?? 'Something went wrong. Please try again.');
      },
    });
  }
}