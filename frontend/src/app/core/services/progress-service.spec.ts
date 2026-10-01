import { ProgressService } from './progress-service';

describe('Dummy learner progress', () => {
  it('starts with six weeks of sample history', () => {
    const service = new ProgressService();
    expect(service.progress().history?.length).toBe(42);
    expect(service.progress().exercisesCompleted).toBe(300);
    expect(service.progress().skills.length).toBe(4);
  });

  it('updates the graph and totals when an activity is completed', () => {
    const service = new ProgressService();
    const before = service.progress();
    service.recordAttempt({ exerciseId: 1, answer: 'word', correct: true, responseTime: 500 }, 'Reading fluency');
    expect(service.progress().exercisesCompleted).toBe(before.exercisesCompleted + 1);
    expect(service.progress().history?.at(-1)?.completed).toBe(11);
    expect(service.progress().history?.at(-1)?.accuracy).toBe(82);
  });
});
