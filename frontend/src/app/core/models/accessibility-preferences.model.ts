import { ReadingFont } from './reading-font.model';

export interface AccessibilityPreferences {
  readingFont: ReadingFont;
  fontSize: 'comfortable' | 'large' | 'extra-large';
  letterSpacing: 'standard' | 'wide' | 'wider';
  lineSpacing: 'standard' | 'relaxed' | 'wide';
  textToSpeech: boolean;
  currentLineHighlight: boolean;
  reducedClutter: boolean;
  theme: 'light' | 'dark';
}