import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { RealWorld } from './real-world';
import { DailyRealLife, DailyRealLifeAttempt } from '../../core/models/daily-real-life.model';
import { ProgressService } from '../../core/services/progress-service';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';

const dailyUrl = '/assessments/real_life/daily/';
const scenario = (index: number, completed = false): DailyRealLifeAttempt => ({
  attempt_id: `attempt-${index}`,
  exercise: { id: `scenario-${index}`, title: `Getting ready ${index}`, context: 'GETTING READY',
    information: ['Leave home at 3:30 PM.'], question: 'What should you do now?', options: ['Get ready', 'Go to bed'] },
  completed_at: completed ? '2026-10-02T10:00:00Z' : null,
  answer: completed ? 'Get ready' : null, correct: completed ? true : null,
  correct_answer: completed ? 'Get ready' : null,
});
const daily = (count = 0): DailyRealLife => ({
  date: '2026-10-02', daily_limit: 3, completed: count, remaining: 3 - count, locked: count === 3,
  next_available_at: '2026-10-03T00:00:00+03:00', exercises: [1, 2, 3].map(index => scenario(index, index <= count)),
});

describe('RealWorld daily API integration', () => {
  let fixture: ComponentFixture<RealWorld>;
  let http: HttpTestingController;
  let page: RealWorld;
  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [RealWorld], providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(RealWorld);
    page = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('loads saved completion status and skips completed scenarios', () => {
    expect(fixture.nativeElement.textContent).toContain('Loading your daily scenarios');
    http.expectOne(dailyUrl).flush(daily(1));
    fixture.detectChanges();
    expect(page.active()?.attempt_id).toBe('attempt-2');
    expect(fixture.nativeElement.textContent).toContain('1 of 3 completed today');
    expect(fixture.nativeElement.querySelectorAll('.daily-scenarios .completed')).toHaveLength(1);
    expect(page.exercise()?.content_data.items?.[0].correct_option_id).toBeUndefined();
  });

  it('submits the chosen option and uses backend correctness after saving', () => {
    http.expectOne(dailyUrl).flush(daily());
    fixture.detectChanges();
    const child = fixture.debugElement.query(By.directive(ExcerciseComponent)).componentInstance as ExcerciseComponent;
    child.selected.set('Get ready');
    child.submit();
    expect(page.saving()).toBe(true);
    expect(page.feedback()).toBe(false);
    const record = vi.spyOn(TestBed.inject(ProgressService), 'recordAttempt');
    const request = http.expectOne('/assessments/real_life/attempt-1/complete/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ answer: 'Get ready' });
    request.flush(scenario(1, true));
    fixture.detectChanges();
    expect(page.lastAttempt()?.correct).toBe(true);
    expect(record).toHaveBeenCalledTimes(1);
    expect(fixture.nativeElement.textContent).toContain('Nice work!');
    expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
    page.onCompleted({ exerciseId: 'attempt-1', answer: 'Go to bed', correct: false, responseTime: 1 });
    http.expectNone('/assessments/real_life/attempt-1/complete/');
    page.tryAnother();
    http.expectOne(dailyUrl).flush(daily(1));
    expect(page.active()?.attempt_id).toBe('attempt-2');
  });

  it('preserves pending answers and retries saving without counting failed requests', () => {
    http.expectOne(dailyUrl).flush(daily());
    const record = vi.spyOn(TestBed.inject(ProgressService), 'recordAttempt');
    page.onCompleted({ exerciseId: 'attempt-1', answer: 'Go to bed', correct: true, responseTime: 100 });
    page.onCompleted({ exerciseId: 'attempt-1', answer: 'Get ready', correct: true, responseTime: 100 });
    http.expectOne('/assessments/real_life/attempt-1/complete/').flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(record).not.toHaveBeenCalled();
    expect(page.daily()?.completed).toBe(0);
    expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
    page.saveCompletion();
    const retry = http.expectOne('/assessments/real_life/attempt-1/complete/');
    expect(retry.request.body).toEqual({ answer: 'Go to bed' });
    retry.flush({ ...scenario(1, true), answer: 'Go to bed', correct: false });
    expect(page.lastAttempt()?.correct).toBe(false);
    expect(record).toHaveBeenCalledTimes(1);
    expect(page.daily()?.completed).toBe(1);
  });

  it('does not allow another scenario once all three are complete, including on reload', () => {
    http.expectOne(dailyUrl).flush(daily(2));
    page.onCompleted({ exerciseId: 'attempt-3', answer: 'Get ready', correct: false, responseTime: 100 });
    http.expectOne('/assessments/real_life/attempt-3/complete/').flush(scenario(3, true));
    expect(page.daily()?.locked).toBe(true);
    page.tryAnother();
    http.expectOne(dailyUrl).flush(daily(3));
    fixture.detectChanges();
    expect(page.active()).toBeNull();
    expect(fixture.nativeElement.textContent).toContain("You've completed all your real-life scenarios for today");
    expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
    page.onCompleted({ exerciseId: 'attempt-3', answer: 'Get ready', correct: true, responseTime: 100 });
    http.expectNone('/assessments/real_life/attempt-3/complete/');
  });

  it('recovers from load errors and expired scenarios', () => {
    http.expectOne(dailyUrl).flush({}, { status: 503, statusText: 'Unavailable' });
    expect(page.loadError()).toContain('Please try again');
    page.loadDaily();
    http.expectOne(dailyUrl).flush(daily());
    page.onCompleted({ exerciseId: 'attempt-1', answer: 'Get ready', correct: false, responseTime: 100 });
    http.expectOne('/assessments/real_life/attempt-1/complete/').flush({}, { status: 409, statusText: 'Conflict' });
    expect(page.expired()).toBe(true);
    page.saveCompletion();
    http.expectNone('/assessments/real_life/attempt-1/complete/');
    page.loadDaily();
    http.expectOne(dailyUrl).flush({ ...daily(), date: '2026-10-03' });
    expect(page.pendingAttempt()).toBeNull();
    expect(page.expired()).toBe(false);
  });
});
