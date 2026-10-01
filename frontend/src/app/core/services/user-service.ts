import { DOCUMENT } from '@angular/common';
import { Inject, Injectable, signal } from '@angular/core';
import { LearnerProfile } from '../models/learner-profile.model';
import { AccessibilityPreferences } from '../models/accessibility-preferences.model';
import { defaultProfile } from './dummy_data';

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly learner = signal<LearnerProfile>(structuredClone(defaultProfile));
  readonly profile = this.learner.asReadonly();
  private readonly assessmentDone = signal(false);
  readonly assessmentCompleted = this.assessmentDone.asReadonly();

  completeAssessment(): void {
    this.assessmentDone.set(true);
  }
  readonly fontSize = signal<AccessibilityPreferences['fontSize']>('comfortable');

  constructor(@Inject(DOCUMENT) private readonly document: Document) {}

  save(profile: LearnerProfile): void {
    this.learner.set(profile);
    this.apply(profile);
  }

  apply(profile: LearnerProfile): void {
    const root = this.document.documentElement;
    root.dataset['theme'] = profile.preferences.theme;
    this.applyReadingFont(profile.preferences.readingFont);
    this.applyFontSize(profile.preferences.fontSize);
    root.dataset['letterSpacing'] = profile.preferences.letterSpacing;
    root.dataset['lineSpacing'] = profile.preferences.lineSpacing;
    root.dataset['reducedClutter'] = String(profile.preferences.reducedClutter);
  }

  applyReadingFont(readingFont: AccessibilityPreferences['readingFont']): void {
    const fonts: Record<AccessibilityPreferences['readingFont'], string> = {
      default: "'DM Sans', sans-serif",
      lexend: "'Lexend', sans-serif",
      opendyslexic: "'OpenDyslexic', sans-serif",
    };
    const root = this.document.documentElement;
    root.dataset['readingFont'] = readingFont;
    root.style.setProperty('--reading-font-family', fonts[readingFont]);
  }

  applyFontSize(fontSize: AccessibilityPreferences['fontSize']): void {
    const profileTextSizes: Record<
      AccessibilityPreferences['fontSize'],
      {
        fieldLabel: string;
        fieldHint: string;
        toggleLabel: string;
        toggleDescription: string;
        sectionDescription: string;
        previewLabel: string;
      }
    > = {
      comfortable: {
        fieldLabel: '13px',
        fieldHint: '10px',
        toggleLabel: '11px',
        toggleDescription: '9px',
        sectionDescription: '10px',
        previewLabel: '9px',
      },
      large: {
        fieldLabel: '15px',
        fieldHint: '12px',
        toggleLabel: '13px',
        toggleDescription: '11px',
        sectionDescription: '12px',
        previewLabel: '11px',
      },
      'extra-large': {
        fieldLabel: '17px',
        fieldHint: '14px',
        toggleLabel: '15px',
        toggleDescription: '13px',
        sectionDescription: '14px',
        previewLabel: '13px',
      },
    };
    const sizes = profileTextSizes[fontSize];
    this.fontSize.set(fontSize);
    const root = this.document.documentElement;
    root.dataset['fontSize'] = fontSize;
    root.style.setProperty('--profile-field-label-size', sizes.fieldLabel);
    root.style.setProperty('--profile-field-hint-size', sizes.fieldHint);
    root.style.setProperty('--profile-toggle-label-size', sizes.toggleLabel);
    root.style.setProperty('--profile-toggle-description-size', sizes.toggleDescription);
    root.style.setProperty('--profile-section-description-size', sizes.sectionDescription);
    root.style.setProperty('--profile-preview-label-size', sizes.previewLabel);
  }
}
