import { provideRouter } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Dashboard } from './dashboard';
import { UserService } from '../../core/services/user-service';
import { AuthService } from '../../core/services/auth-service';

const saved = { exercisesCompleted: 23, currentStreak: 4, skills: [
  { id: 1, name: 'Comprehension', progress: 64, change: -2, metric: 'score' },
], achievements: [], history: [] };

describe('Dashboard saved statistics', () => {
  const profile = signal({ name: 'Maya', ageGroup: '19_plus' });
  let http: HttpTestingController;
  beforeEach(() => {
    profile.set({ name: 'Maya', ageGroup: '19_plus' });
    TestBed.configureTestingModule({ imports: [Dashboard], providers: [
      provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
      { provide: UserService, useValue: { profile, assessmentCompleted: () => true } },
      { provide: AuthService, useValue: { token: () => 'learner-token' } },
    ] });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('shows authenticated totals and skill results in the adult dashboard', () => {
    const fixture = TestBed.createComponent(Dashboard);
    http.expectOne('/practice/progress/').flush(saved);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('23');
    expect(fixture.nativeElement.textContent).toContain('4 days');
    expect(fixture.nativeElement.textContent).toContain('64%');
    expect(fixture.nativeElement.textContent).toContain('-2 points since your previous result');
  });

  it('uses those same totals for child stars and levels', () => {
    profile.set({ name: 'Maya', ageGroup: 'under_12' });
    const fixture = TestBed.createComponent(Dashboard);
    http.expectOne('/practice/progress/').flush(saved);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('23');
    expect(fixture.nativeElement.textContent).toContain('Level 3');
    expect(fixture.nativeElement.textContent).toContain('7 more activities');
    expect(fixture.nativeElement.textContent).not.toContain('Sample progress data');
  });
});
