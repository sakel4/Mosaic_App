import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RealWorld } from './real-world';
import { RealWorldService } from '../../core/services/real-world-service';
import { vi } from 'vitest';

describe('RealWorld', () => {
  let component: RealWorld;
  let fixture: ComponentFixture<RealWorld>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RealWorld],
      providers: [{ provide: RealWorldService, useValue: {
        nextScenario: () => ({
          id: 'bus', title: 'Catch the bus', context: 'Travel', information: ['Bus leaves at 10:00'],
          exercise: { id: 1, type: 'comprehension', skill: 'Everyday reading', difficulty: 2,
            content: { prompt: 'When does the bus leave?', options: ['10:00', '11:00'],
              correctAnswer: '10:00', explanation: 'The bus leaves at 10:00.' } },
        }),
        recordAttempt: vi.fn(),
      } }],
    }).compileComponents();

    fixture = TestBed.createComponent(RealWorld);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('hides the scenario after answering and restores it for another attempt', () => {
    fixture.detectChanges();
    const page = fixture.nativeElement as HTMLElement;
    expect(page.querySelector('.travel-board')).not.toBeNull();
    component.onCompleted({ exerciseId: 1, answer: '10:00', correct: true, responseTime: 100 });
    fixture.detectChanges();
    expect(page.querySelector('.travel-board')).toBeNull();
    expect(page.querySelector('.scenario-heading')).toBeNull();
    expect(page.querySelector('.real-life-aside')).toBeNull();
    expect(page.querySelector('app-excercise-component')).toBeNull();
    const button = page.querySelector<HTMLButtonElement>('app-exercise-feedback-component button')!;
    expect(button.textContent).toContain('Try another scenario');
    button.click();
    fixture.detectChanges();
    expect(page.querySelector('.travel-board')).not.toBeNull();
    expect(page.querySelector('app-excercise-component')).not.toBeNull();
    expect(page.querySelector('app-exercise-feedback-component')).toBeNull();
  });
});
