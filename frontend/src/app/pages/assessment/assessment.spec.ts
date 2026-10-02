import { provideRouter } from '@angular/router';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Assessment } from './assessment';
import { provideHttpClient } from '@angular/common/http';
import { vi } from 'vitest';

describe('Assessment', () => {
  let component: Assessment;
  let fixture: ComponentFixture<Assessment>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Assessment],
      providers: [provideRouter([]), provideHttpClient()],
    }).compileComponents();

    fixture = TestBed.createComponent(Assessment);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Loading your assessment...');
    await vi.waitFor(() => expect(component.loading()).toBe(false));
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('displays the supplied 12–15 assessment and advances to the next prompt', async () => {
    expect(component.exercises).toHaveLength(8);
    expect(fixture.nativeElement.textContent).toContain('Say smile in your head.');
    expect(fixture.nativeElement.textContent).toContain('mile');
    component.onCompleted({ exerciseId: 1, answer: '1', correct: true, responseTime: 1000 });
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Nice work!');
    component.nextExercise();
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Say plane in your head.');
    expect(fixture.nativeElement.textContent).toContain('Activity 2 of 8');
  });
});
