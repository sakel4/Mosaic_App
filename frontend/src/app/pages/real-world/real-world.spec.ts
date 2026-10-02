import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { By } from '@angular/platform-browser';
import { RealWorld } from './real-world';
import { RealLifeSet } from '../../core/models/real-life-set.model';
import { ExcerciseComponent } from '../../shared/components/exercise-component/exercise-component';
import { ProgressService } from '../../core/services/progress-service';
import { vi } from 'vitest';

const setUrl = '/real_life_set/';
const evaluateUrl = '/real_life_set/evaluate/';
const realLifeSet = (): RealLifeSet => ({
  id: 'set-1', category: 'Getting ready',
  age_group: { '12_15': [1, 2, 3].map(index => ({
    id: `set-1_0${index}`, title: `Getting ready ${index}`, context: 'GETTING READY',
    information: ['Leave home at 3:30 PM.'], question: 'What should you do now?', options: ['Get ready', 'Go to bed'],
    correct_answer: ['Get ready'],
  })) },
});

describe('RealWorld real-life set integration', () => {
  let fixture: ComponentFixture<RealWorld>;
  let http: HttpTestingController;
  let page: RealWorld;
  const recordAttempt = vi.fn();
  beforeEach(() => {
    recordAttempt.mockClear();
    localStorage.removeItem('mosaic.realWorld.completedAt');
    TestBed.configureTestingModule({ imports: [RealWorld], providers: [
      provideHttpClient(), provideHttpClientTesting(),
      { provide: ProgressService, useValue: { recordAttempt } },
    ] });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(RealWorld);
    page = fixture.componentInstance;
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  it('loads a generated set and shows the first scenario', () => {
    expect(fixture.nativeElement.textContent).toContain('Loading your scenarios');
    const request = http.expectOne(setUrl);
    expect(request.request.method).toBe('POST');
    request.flush(realLifeSet());
    fixture.detectChanges();
    expect(page.active()?.id).toBe('set-1_01');
    expect(fixture.nativeElement.textContent).toContain('0 of 3 completed');
    expect(fixture.nativeElement.querySelectorAll('.board-line')).toHaveLength(1);
  });

  it('shows feedback after each answer and evaluates the set after the last one', () => {
    http.expectOne(setUrl).flush(realLifeSet());
    fixture.detectChanges();
    const choices = ['Get ready', 'Go to bed', 'Get ready'];
    ['set-1_01', 'set-1_02', 'set-1_03'].forEach((id, position) => {
      const child = fixture.debugElement.query(By.directive(ExcerciseComponent)).componentInstance as ExcerciseComponent;
      child.selected.set(choices[position]);
      child.submit();
      fixture.detectChanges();
      expect(page.results()[id]).toBe(choices[position] === 'Get ready');
      expect(fixture.nativeElement.querySelector('app-exercise-feedback-component')).not.toBeNull();
      expect(fixture.nativeElement.querySelector('app-excercise-component')).toBeNull();
      page.next();
      fixture.detectChanges();
    });
    const evaluate = http.expectOne(`${evaluateUrl}`);
    expect(evaluate.request.body).toEqual({
      real_life_set_id: 'set-1', answers: { 'set-1_01': true, 'set-1_02': false, 'set-1_03': true },
    });
    evaluate.flush({ id: 'eval-1', correct: 2, total: 3 });
    fixture.detectChanges();
    expect(page.finished()).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('You got 2 of 3 right.');
  });

  it('lets the learner retry saving results after an evaluation error', () => {
    http.expectOne(setUrl).flush(realLifeSet());
    fixture.detectChanges();
    for (let position = 0; position < 3; position++) {
      page.onCompleted({ exerciseId: `set-1_0${position + 1}`, answer: 'Get ready', correct: true, responseTime: 1 });
      page.next();
    }
    http.expectOne(evaluateUrl).flush({}, { status: 503, statusText: 'Unavailable' });
    expect(page.evaluateError()).toContain('Please try again');
    page.submitEvaluation();
    http.expectOne(evaluateUrl).flush({ id: 'eval-1', correct: 3, total: 3 });
    expect(page.evaluation()?.correct).toBe(3);
    expect(page.evaluateError()).toBe('');
  });

  it('ignores answers for a different exercise', () => {
    http.expectOne(setUrl).flush(realLifeSet());
    page.onCompleted({ exerciseId: 'other', answer: 'Get ready', correct: false, responseTime: 1 });
    expect(page.feedback()).toBe(false);
    expect(page.results()).toEqual({});
    expect(recordAttempt).not.toHaveBeenCalled();
  });

  it('records each answered scenario toward stars and stats', () => {
    http.expectOne(setUrl).flush(realLifeSet());
    page.onCompleted({ exerciseId: 'set-1_01', answer: 'Go to bed', correct: true, responseTime: 1 });
    expect(recordAttempt).toHaveBeenCalledWith(
      expect.objectContaining({ exerciseId: 'set-1_01', correct: false }), 'Everyday reading');
  });

  it('recovers from load errors and requests a new set', () => {
    http.expectOne(setUrl).flush({}, { status: 503, statusText: 'Unavailable' });
    expect(page.loadError()).toContain('Please try again');
    page.loadSet();
    http.expectOne(setUrl).flush(realLifeSet());
    expect(page.loadError()).toBe('');
    expect(page.exercises()).toHaveLength(3);
  });
});
