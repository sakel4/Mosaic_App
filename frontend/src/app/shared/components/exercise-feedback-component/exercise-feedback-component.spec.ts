import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExerciseFeedbackComponent } from './exercise-feedback-component';

describe('ExerciseFeedbackComponent', () => {
  let component: ExerciseFeedbackComponent;
  let fixture: ComponentFixture<ExerciseFeedbackComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExerciseFeedbackComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ExerciseFeedbackComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
