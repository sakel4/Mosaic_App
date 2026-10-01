import { ActivityType } from './activity-type.model';

export interface Activity {
  id: number;
  type: ActivityType;
  skill: string;
  title: string;
  description: string;
  estimatedMinutes: number;
  difficulty: number;
  reason: string;
}
