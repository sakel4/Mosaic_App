import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { Progress } from './progress';
import { UserService } from '../../core/services/user-service';
import { AuthService } from '../../core/services/auth-service';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';

const saved = { exercisesCompleted: 12, currentStreak: 3, skills: [
  { id: 1, name: 'Reading fluency', progress: 72, change: 7, metric: 'score' },
], achievements: [], history: [] };

describe('Age-appropriate saved progress', () => {
  const profile = signal({ ageGroup: 'under_12', currentFocus: [] });
  let http: HttpTestingController;
  beforeEach(() => {
    profile.set({ ageGroup: 'under_12', currentFocus: [] });
    TestBed.configureTestingModule({ imports: [Progress], providers: [
      provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
      { provide: UserService, useValue: { profile } },
      { provide: AuthService, useValue: { token: () => 'learner-token' } },
    ] });
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('loads saved stars for children and skill scores for older learners', () => {
    const fixture = TestBed.createComponent(Progress);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Loading your progress');
    http.expectOne('/practice/progress/').flush(saved);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-kid-progress')).toBeTruthy();
    expect(fixture.nativeElement.textContent).toContain('Level 2');
    expect(fixture.nativeElement.textContent).not.toContain('Sample progress data');
    profile.set({ ageGroup: '12_15', currentFocus: [] });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-kid-progress')).toBeNull();
    expect(fixture.nativeElement.querySelector('app-progress-chart')).toBeTruthy();
    expect(fixture.nativeElement.textContent).toContain('72%');
    expect(fixture.nativeElement.textContent).toContain('Skill score');
  });

  it('shows a retry when statistics cannot load', () => {
    const fixture = TestBed.createComponent(Progress);
    http.expectOne('/practice/progress/').flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-kid-progress')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Please try again');
    fixture.componentInstance.retryProgress();
    http.expectOne('/practice/progress/').flush({ ...saved, exercisesCompleted: 0, skills: [] });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Level 1');
  });

  it('uploads a report of saved statistics with the recipient email', async () => {
    const page = TestBed.createComponent(Progress).componentInstance;
    http.expectOne('/practice/progress/').flush(saved);
    page.email = ' parent@example.com ';
    const pending = page.downloadReport(true);
    const request = await vi.waitFor(() => http.expectOne('/users/progress/email/'));
    expect(request.request.body.get('email')).toBe('parent@example.com');
    expect(request.request.body.get('pdf').type).toBe('application/pdf');
    expect(request.request.body.get('pdf').name).toBe('mosaic-progress.pdf');
    request.flush({ detail: 'Submitted.' });
    await pending;
    expect(page.reportStatus()).toContain('sent to parent@example.com');
  });
});
