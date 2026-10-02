import { exercises } from '../../../core/services/dummy_data';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExcerciseComponent } from './exercise-component';
import { provideHttpClient } from '@angular/common/http';
import { AssessmentExercise, assessmentExercises } from '../../../core/models/assessment.model';

describe('ExcerciseComponent', () => {
  let component: ExcerciseComponent;
  let fixture: ComponentFixture<ExcerciseComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExcerciseComponent],
      providers: [provideHttpClient()],
    }).compileComponents();

    fixture = TestBed.createComponent(ExcerciseComponent);
    fixture.componentRef.setInput('exercise', exercises[0]);
    fixture.componentRef.setInput('mode', 'practice');
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('renders API option labels and emits IDs for every item', async () => {
    const exercise: AssessmentExercise = {
      position: 1, kind: 'phoneme_manipulation', skill: 'phonological_awareness',
      difficulty: 3, response_type: 'single_choice_set', instruction: 'Listen and choose.',
      content_data: { items: [
        { id: 'a', audio_prompt: 'Remove /s/ from smile.', options: [{ id: '1', text: 'mile' }], correct_option_id: '1' },
        { id: 'b', audio_prompt: 'Remove /p/ from plane.', options: [{ id: '2', text: 'lane' }], correct_option_id: '2' },
      ] },
    };
    fixture.componentRef.setInput('exercise', exercise);
    await fixture.whenStable();
    const attempts: unknown[] = [];
    component.completed.subscribe((attempt) => attempts.push(attempt));
    expect(fixture.nativeElement.textContent).toContain('mile');
    component.choose('1');
    component.submit();
    expect(attempts).toHaveLength(0);
    expect(component.content().prompt).toContain('plane');
    expect(component.selected()).toBeNull();
    component.choose('2');
    component.submit();
    expect(attempts[0]).toMatchObject({ exerciseId: 1, answer: ['1', '2'], correct: true, itemAnswers: { a: '1', b: '2' } });
  });

  it('inherits the language from the REST envelope with the supplied excercises spelling', () => {
    const exercises = assessmentExercises({ assessment: {
      age_group: '12_15', language: 'en', estimated_duration_seconds: 72, type: 'assessment',
      excercises: [{ position: 1, kind: 'phoneme_manipulation', skill: 'phonological_awareness', difficulty: 3,
        response_type: 'single_choice_set', instruction: 'Listen.', content_data: { items: [] } }],
    } });
    expect(exercises[0].language).toBe('en');
  });
});
