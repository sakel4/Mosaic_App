import { DOCUMENT } from '@angular/common';
import { inject, Inject, Injectable, signal } from '@angular/core';
import { LearnerProfile } from '../models/learner-profile.model';
import { AccessibilityPreferences } from '../models/accessibility-preferences.model';
import { defaultProfile } from './dummy_data';
import { HttpClient } from '@angular/common/http';
import { map, Observable, tap } from 'rxjs';
import { User } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);
  private readonly learner = signal<LearnerProfile>(structuredClone(defaultProfile));
  readonly profile = this.learner.asReadonly();
  private readonly assessmentDone = signal(false);
  readonly assessmentCompleted = this.assessmentDone.asReadonly();
  readonly fontSize = signal<AccessibilityPreferences['fontSize']>('comfortable');

  constructor(@Inject(DOCUMENT) private readonly document: Document) {}

  load(): Observable<LearnerProfile> {
    return this.http.get<User>('/users/me/').pipe(
      tap((me) => this.assessmentDone.set(me.assessment_completed)),
      map((me) => this.fromUser(me)),
      tap((profile) => {
        this.learner.set(profile);
        this.apply(profile);
      }),
    );
  }

  save(profile: LearnerProfile): Observable<LearnerProfile> {
    const [first_name, ...rest] = profile.name.trim().split(/\s+/);
    return this.http
      .patch<User>('/users/me/', {
        first_name,
        last_name: rest.join(' '),
        profile: {
          age_group: profile.ageGroup,
          interests: profile.interests,
          learning_goal: profile.learningGoals[0] ?? '',
          preferences: {
            reading_font: profile.preferences.readingFont === 'opendyslexic'
              ? 'opens_dyslexic' : profile.preferences.readingFont,
            font_size: profile.preferences.fontSize === 'extra-large'
              ? 'x_large' : profile.preferences.fontSize,
            letter_spacing: profile.preferences.letterSpacing,
            line_spacing: profile.preferences.lineSpacing,
            text_to_speech: profile.preferences.textToSpeech,
            current_line_highlight: profile.preferences.currentLineHighlight,
            reduced_clutter: profile.preferences.reducedClutter,
            theme: profile.preferences.theme,
          },
        },
      })
      .pipe(
        tap((me) => this.assessmentDone.set(me.assessment_completed)),
        map((me) => this.fromUser(me)),
        tap((saved) => {
          this.learner.set(saved);
          this.apply(saved);
        }),
      );
  }

  private fromUser(user: User): LearnerProfile {
    const profile = user.profile;
    const preferences = profile?.preferences;
    return {
      name: `${user.first_name} ${user.last_name}`.trim(),
      ageGroup: profile?.age_group ?? '',
      interests: profile?.interests ?? [],
      learningGoals: profile?.learning_goal ? [profile.learning_goal] : [],
      currentFocus: profile?.current_focus ?? [],
      preferences: preferences ? {
        readingFont: preferences.reading_font === 'opens_dyslexic'
          ? 'opendyslexic' : preferences.reading_font,
        fontSize: preferences.font_size === 'x_large' ? 'extra-large' : preferences.font_size,
        letterSpacing: preferences.letter_spacing,
        lineSpacing: preferences.line_spacing,
        textToSpeech: preferences.text_to_speech,
        currentLineHighlight: preferences.current_line_highlight,
        reducedClutter: preferences.reduced_clutter,
        theme: preferences.theme,
      } : { ...defaultProfile.preferences },
    };
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
