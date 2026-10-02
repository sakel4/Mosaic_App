export interface LearnerSkill {
  id: number;
  name: string;
  progress: number;
  change: number;
  metric?: 'score' | 'accuracy';
}
