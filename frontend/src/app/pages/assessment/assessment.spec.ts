import { vi } from 'vitest';
import { UserService } from '../../core/services/user-service';
import { User } from '../../core/models/user.model';
import { of } from 'rxjs';
import { Router, provideRouter } from '@angular/router';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Assessment } from './assessment';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import assessmentFixture from '../../core/data/assessment-under-12.json';

describe('Assessment', () => {
  let component: Assessment;
  let fixture: ComponentFixture<Assessment>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Assessment],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(Assessment);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Loading your assessment...');
    const request = TestBed.inject(HttpTestingController).expectOne('/assessments/initial/');
    expect(request.request.method).toBe('GET');
    request.flush(assessmentFixture);
    await fixture.whenStable();
  });

  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('displays the supplied 12–15 assessment and advances to the next prompt', async () => {
    expect(component.exercises).toHaveLength(7);
    expect(fixture.nativeElement.textContent).toContain('Which option shows the sounds in fish');
    expect(fixture.nativeElement.textContent).toContain('/f/ /i/ /sh/');
    component.onCompleted({ exerciseId: 1, answer: '1', correct: true, responseTime: 1000 });
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Nice work!');
    expect(component.lastAttempt()?.answer).toBe('');
    expect(component.lastAttempt()?.itemAnswers).toBeUndefined();
    component.nextExercise();
    expect(component.lastAttempt()).toBeNull();
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('moon');
    expect(fixture.nativeElement.textContent).toContain('Activity 2 of 7');
  });
  it('removes feedback before clearing the final attempt while navigation is pending', async () => {
    vi.spyOn(TestBed.inject(UserService), 'completeAssessment').mockReturnValue(of({} as User));
    vi.spyOn(TestBed.inject(Router), 'navigate').mockReturnValue(new Promise<boolean>(() => {}));
    component.index.set(component.exercises.length - 1);
    component.onCompleted({ exerciseId: 'last', answer: '7 1 4', correct: true, responseTime: 100 });
    await fixture.whenStable();
    component.nextExercise();
    fixture.detectChanges();
    expect(component.lastAttempt()).toBeNull();
    expect(component.feedback()).toBe(false);
    expect(fixture.nativeElement.querySelector('app-exercise-feedback-component')).toBeNull();
    expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
  });

});
