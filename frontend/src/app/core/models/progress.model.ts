import { Achievement } from './achievement.model';
import { LearnerSkill } from './learner-skill.model';

export interface Progress {
  exercisesCompleted: number;
  currentStreak: number;
  skills: LearnerSkill[];
  achievements: Achievement[];
  hourlyHistory?: { date: string; hour: number; completed: number; accuracy: number | null }[];
  timeZone?: string;
  history?: { date: string; completed: number; accuracy: number | null }[];
}
