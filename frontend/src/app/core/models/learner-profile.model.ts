import { AccessibilityPreferences } from './accessibility-preferences.model';

export interface LearnerProfile {
  name: string;
  ageGroup: string;
  learningGoals: string[];
  interests: string[];
  preferences: AccessibilityPreferences;
  currentFocus: string;
}
