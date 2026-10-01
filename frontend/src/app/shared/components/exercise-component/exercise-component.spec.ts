import { exercises } from '../../../core/services/dummy_data';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExcerciseComponent } from './exercise-component';

describe('ExcerciseComponent', () => {
  let component: ExcerciseComponent;
  let fixture: ComponentFixture<ExcerciseComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExcerciseComponent],
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
});
