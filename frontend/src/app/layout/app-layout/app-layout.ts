import { UserService } from '../../core/services/user-service';
import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  imports: [RouterLink, RouterOutlet, RouterLinkActive],
  selector: 'app-app-layout',
  styleUrl: './app-layout.scss',
  templateUrl: './app-layout.html',
})
export class AppLayout {
  private readonly users = inject(UserService);
  private readonly router = inject(Router);
  readonly navItems = [
    { label: 'Home', path: '/dashboard', icon: '⌂' },
    { label: 'Practice', path: '/practice', icon: '◷' },
    { label: 'Real Life', path: '/real-world', icon: '⌖' },
    { label: 'Progress', path: '/progress', icon: '↗' },
    { label: 'Profile', path: '/profile', icon: '○' },
  ];

  constructor() {
    this.users.load().subscribe({
      next: (profile) => console.log('profile', profile),
      error: (err) => console.error('profile load failed', err),
    });
  }

  get name(): string {
    return this.users.profile().name;
  }

  get initials(): string {
    return this.name
      .split(/\s+/)
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }

  goToProfile(): void {
    void this.router.navigate(['/profile']);
  }
}
