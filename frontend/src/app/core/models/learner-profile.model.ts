import { AccessibilityPreferences } from './accessibility-preferences.model';

export const LEARNING_GOALS = [
  'Read faster',
  'Read words with confidence',
  'Understand what I read',
  'Spelling',
  'General reading support',
  'I’m not sure yet',
];

export const DEFAULT_LEARNING_GOAL = 'General reading support';

export interface SkillFocus {
  skill: string;
  score: number;
}

export interface LearnerProfile {
  name: string;
  ageGroup: string;
  learningGoals: string[];
  interests: string[];
  preferences: AccessibilityPreferences;
  currentFocus: SkillFocus[];
}
