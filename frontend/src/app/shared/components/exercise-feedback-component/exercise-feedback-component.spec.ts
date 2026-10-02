import { ComponentFixture, TestBed } from '@angular/core/testing';
import { exercises } from '../../../core/services/dummy_data';
import { ExerciseFeedbackComponent } from './exercise-feedback-component';

describe('ExerciseFeedbackComponent', () => {
  let component: ExerciseFeedbackComponent;
  let fixture: ComponentFixture<ExerciseFeedbackComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExerciseFeedbackComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ExerciseFeedbackComponent);
    fixture.componentRef.setInput('exercise', exercises[0]);
    fixture.componentRef.setInput('attempt', { exerciseId: 1, answer: '1', correct: true, responseTime: 100 });
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('shows wrong feedback instead of a saved-response message', async () => {
    fixture.componentRef.setInput('attempt', { exerciseId: 'uuid', answer: '1', correct: false, evaluated: false, responseTime: 100 });
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Not quite ? keep exploring');
    expect(fixture.nativeElement.textContent).not.toContain('Response saved');
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(fixture.nativeElement.textContent).toContain('Nice work!');
  });
});
