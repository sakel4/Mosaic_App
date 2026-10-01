import { AccessibilityPreferences } from './accessibility-preferences.model';

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
