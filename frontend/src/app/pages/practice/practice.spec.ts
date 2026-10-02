import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Practice } from './practice';
import assessmentFixture from '../../core/data/assessment-under-12.json';

describe('Practice API integration', () => {
  let fixture: ComponentFixture<Practice>;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [Practice], providers: [
      provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
    ] });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Practice);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('loads backend exercises and uses their count for the practice set', () => {
    expect(fixture.nativeElement.textContent).toContain('Loading your practice');
    expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
    const request = http.expectOne('/assessments/exercise/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({});
    request.flush(assessmentFixture);
    fixture.detectChanges();
    const page = fixture.componentInstance;
    expect(page.sessionSize()).toBe(7);
    expect(page.exercise()?.id).toBe(assessmentFixture[0].excercises[0].id);
    expect(fixture.nativeElement.textContent).toContain('Which option shows the sounds in fish');
    for (let i = 0; i < page.sessionSize(); i++) {
      page.onCompleted({ exerciseId: page.exercise()!.id!, answer: '1', correct: true, responseTime: 100 });
      page.continuePractice();
    }
    fixture.detectChanges();
    expect(page.setComplete()).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('You completed 7 activities');
    page.startAnotherSet();
    http.expectOne('/assessments/exercise/').flush(assessmentFixture);
    expect(page.completedInSet()).toBe(0);
  });

  it('shows an error and retries without displaying dummy exercises', () => {
    http.expectOne('/assessments/exercise/').flush({ detail: 'Not implemented.' }, { status: 501, statusText: 'Not Implemented' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Could not load your practice');
    fixture.nativeElement.querySelector('button').click();
    http.expectOne('/assessments/exercise/').flush(assessmentFixture);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-excercise-component')).not.toBeNull();
  });

  it('handles an empty response without substituting dummy data', () => {
    http.expectOne('/assessments/exercise/').flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No practice activities are available');
    expect(fixture.componentInstance.exercise()).toBeNull();
  });
});
