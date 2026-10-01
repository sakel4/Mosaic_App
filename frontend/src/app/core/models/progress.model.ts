import { Achievement } from './achievement.model';
import { LearnerSkill } from './learner-skill.model';

export interface Progress {
  exercisesCompleted: number;
  currentStreak: number;
  skills: LearnerSkill[];
  achievements: Achievement[];
  history?: { date: string; completed: number; accuracy: number | null }[];
}
