import { AccessibilityPreferences } from './accessibility-preferences.model';
import { SkillFocus } from './learner-profile.model';

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'learner' | 'admin';
  assessment_completed: boolean;
  created_at: string;
  profile: {
    age_group: string;
    interests: string[];
    learning_goal: string;
    current_focus: SkillFocus[];
    preferences: {
      reading_font: 'default' | 'lexend' | 'opens_dyslexic';
      font_size: 'comfortable' | 'large' | 'x_large';
      letter_spacing: AccessibilityPreferences['letterSpacing'];
      line_spacing: AccessibilityPreferences['lineSpacing'];
      text_to_speech: boolean;
      current_line_highlight: boolean;
      reduced_clutter: boolean;
      theme: AccessibilityPreferences['theme'];
    } | null;
  } | null;
}
