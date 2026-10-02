import { Progress } from '../models/progress.model';

export async function createProgressReport(progress: Progress) {
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF();
  let y = 22;
  const line = (text: string, size = 11) => {
    doc.setFontSize(size);
    const rows: string[] = doc.splitTextToSize(text, 170);
    for (const row of rows) {
      if (y > 275) { doc.addPage(); y = 22; }
      doc.text(row, 20, y);
      y += size * 0.5 + 3;
    }
  };
  line('Mosaic - Progress report', 20);
  line(`Generated: ${new Date().toLocaleDateString('en-GB')}`);
  line(`Activities completed: ${progress.exercisesCompleted}`);
  line(`Current practice streak: ${progress.currentStreak} days`);
  y += 6;
  line('Skill results', 15);
  for (const skill of progress.skills) line(`${skill.name}: ${skill.progress}% (${skill.metric === 'score' ? 'skill score' : 'practice accuracy'}); latest change: ${skill.change > 0 ? '+' : ''}${skill.change} points`);
  y += 6;
  line('Milestones', 15);
  for (const badge of progress.achievements) line(badge.title);
  y += 6;
  line('Daily results - last six weeks', 15);
  line('Date / Activities completed / Correct answers (%)');
  for (const day of progress.history ?? []) {
    line(`${day.date} / ${day.completed} / ${day.accuracy === null ? 'Not scored' : `${day.accuracy}%`}`);
  }
  return doc;
}

export async function downloadProgressReport(progress: Progress): Promise<void> {
  const doc = await createProgressReport(progress);
  await doc.save('mosaic-progress.pdf', { returnPromise: true });
}
