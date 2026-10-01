import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { vi } from 'vitest';
import { Practice } from '../../pages/practice/practice';
import { Assessment } from '../../pages/assessment/assessment';
import { Profile } from '../../pages/profile/profile';
import { Dashboard } from '../../pages/dashboard/dashboard';
import { AuthService } from './auth-service';
import { ProgressService } from './progress-service';
import { UserService } from './user-service';
import { Exercise } from '../models/exercise.model';

describe('Page service connections', () => {
  const navigate = vi.fn().mockResolvedValue(true);

  beforeEach(() => {
    navigate.mockClear();
    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: { navigate } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: new Map() } } },
        { provide: AuthService, useValue: { logout: vi.fn() } },
      ],
    });
  });

  const attempt = (exercise: Exercise) => ({
    exerciseId: exercise.id,
    answer: exercise.content.correctAnswer,
    correct: true,
    responseTime: 1000,
  });

  it('records six practice attempts and starts a fresh set', () => {
    const page = TestBed.runInInjectionContext(() => new Practice());
    const progress = TestBed.inject(ProgressService);
    const initialCount = progress.progress().exercisesCompleted;
    const firstExerciseId = page.exercise().id;
    for (let index = 0; index < page.sessionSize; index++) {
      page.onCompleted(attempt(page.exercise()));
      page.continuePractice();
      if (index === 0) expect(page.exercise().id).not.toBe(firstExerciseId);
    }
    expect(progress.progress().exercisesCompleted).toBe(initialCount + 6);
    expect(page.setComplete()).toBe(true);
    page.startAnotherSet();
    expect(page.completedInSet()).toBe(0);
    expect(page.setComplete()).toBe(false);
    expect(page.lastAttempt()).toBeNull();
  });

  it('marks assessment complete after the final activity and opens preferences', () => {
    const page = TestBed.runInInjectionContext(() => new Assessment());
    const users = TestBed.inject(UserService);
    const dashboard = TestBed.runInInjectionContext(() => new Dashboard());
    expect(dashboard.assessmentCompleted).toBe(false);
    for (let index = 0; index < page.exercises.length; index++) {
      page.onCompleted(attempt(page.exercise()));
      if (index < page.exercises.length - 1) expect(users.assessmentCompleted()).toBe(false);
      page.nextExercise();
    }
    expect(dashboard.assessmentCompleted).toBe(true);
    expect(navigate).toHaveBeenCalledWith(['/profile'], {
      queryParams: { afterAssessment: 'true' },
    });
    expect(page.index()).toBe(page.exercises.length - 1);
  });

  it('saves profile changes into the shared user state and applies reading settings', () => {
    const users = TestBed.inject(UserService);
    const originalFocus = users.profile().currentFocus;
    const page = TestBed.runInInjectionContext(() => new Profile());
    const dashboard = TestBed.runInInjectionContext(() => new Dashboard());
    page.form.patchValue({ name: 'Maya Rivers', fontSize: 'large', theme: 'dark' });
    page.save();
    expect(dashboard.firstName).toBe('Maya');
    expect(users.profile().currentFocus).toBe(originalFocus);
    expect(users.fontSize()).toBe('large');
    expect(document.documentElement.dataset['theme']).toBe('dark');
    expect(page.saved).toBe(true);
  });

  afterEach(() => {
    const users = TestBed.inject(UserService);
    users.apply({
      ...users.profile(),
      preferences: { ...users.profile().preferences, fontSize: 'comfortable', theme: 'light' },
    });
  });
});
