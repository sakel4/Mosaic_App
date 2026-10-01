import { Progress } from '../models/progress.model';

/** Display-only sample data; never submitted to the progress API. */
export function createProgressPreview(): Progress {
  const today = new Date();
  const history = Array.from({ length: 42 }, (_, index) => {
    const day = new Date(today);
    day.setDate(today.getDate() - 41 + index);
    const date = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
    // Two rest days each week, followed by a five-day practice streak.
    const completed = index % 7 < 2 ? 0 : 10;
    const correct = Math.min(9, 4 + Math.floor(index / 9) + (index % 3 === 0 ? 1 : 0));
    return { date, completed, accuracy: completed ? correct * 10 : null };
  });
  return {
    exercisesCompleted: history.reduce((sum, day) => sum + day.completed, 0),
    currentStreak: 5,
    skills: [
      { id: 1, name: 'Reading fluency', progress: 82, change: 2 },
      { id: 2, name: 'Word recognition', progress: 76, change: 1 },
      { id: 3, name: 'Comprehension', progress: 68, change: -1 },
      { id: 4, name: 'Spelling', progress: 90, change: 0 },
    ],
    achievements: [1, 10, 50, 100].map((count) => ({
      id: count, title: `${count} activities completed`,
      description: 'Every activity is another step forward.', icon: '★',
    })),
    history,
  };
}
