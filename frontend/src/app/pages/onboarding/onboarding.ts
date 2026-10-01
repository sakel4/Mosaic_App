import { UserService } from '../../core/services/user-service';
import { normalizeLearnerInterests } from '../../core/models/learner-interest.model';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AccessibilityPreferences } from '../../core/models/accessibility-preferences.model';
import { LEARNER_INTERESTS } from '../../core/models/learner-interest.model';
import { LearnerInterest } from '../../core/models/learner-interest.model';
import { LearnerProfile } from '../../core/models/learner-profile.model';
import { ReadingFont } from '../../core/models/reading-font.model';
import { InterestPickerComponent } from '../../shared/components/interest-picker-component/interest-picker-component';

@Component({
  imports: [ReactiveFormsModule, RouterLink, InterestPickerComponent],
  selector: 'app-onboarding',
  styleUrl: './onboarding.scss',
  templateUrl: './onboarding.html',
})
export class Onboarding {
  private readonly users = inject(UserService);
  private readonly router = inject(Router);
  readonly step = signal(0);
  readonly goals = [
    'Read faster',
    'Read words with confidence',
    'Understand what I read',
    'Spelling',
    'General reading support',
    'I’m not sure yet',
  ];
  readonly interestOptions = LEARNER_INTERESTS;
  readonly form = new FormGroup({
    name: new FormControl(this.users.profile().name, {
      nonNullable: true,
      validators: [Validators.required],
    }),
    ageGroup: new FormControl(this.users.profile().ageGroup, { nonNullable: true }),
    goal: new FormControl(this.users.profile().learningGoals[0] ?? this.goals[0], {
      nonNullable: true,
    }),
    interests: new FormControl<LearnerInterest[]>(
      normalizeLearnerInterests(this.users.profile().interests),
      { nonNullable: true },
    ),
    fontSize: new FormControl<AccessibilityPreferences['fontSize']>('comfortable', {
      nonNullable: true,
    }),
    readingFont: new FormControl<ReadingFont>('default', { nonNullable: true }),
    letterSpacing: new FormControl<AccessibilityPreferences['letterSpacing']>('standard', {
      nonNullable: true,
    }),
    lineSpacing: new FormControl<AccessibilityPreferences['lineSpacing']>('relaxed', {
      nonNullable: true,
    }),
    theme: new FormControl<AccessibilityPreferences['theme']>('light', { nonNullable: true }),
    textToSpeech: new FormControl(this.users.profile().preferences.textToSpeech, {
      nonNullable: true,
    }),
    currentLineHighlight: new FormControl(true, { nonNullable: true }),
    reducedClutter: new FormControl(false, { nonNullable: true }),
  });

  get previewFont(): string {
    const fonts: Record<ReadingFont, string> = {
      default: "'DM Sans', sans-serif",
      lexend: "'Lexend', sans-serif",
      opendyslexic: "'OpenDyslexic', sans-serif",
    };
    return fonts[this.form.controls.readingFont.value];
  }

  applyReadingFont(): void {
    this.users.applyReadingFont(this.form.controls.readingFont.value);
  }

  get previewSize(): string {
    const sizes: Record<AccessibilityPreferences['fontSize'], string> = {
      comfortable: '14px',
      large: '16px',
      'extra-large': '18px',
    };
    return sizes[this.form.controls.fontSize.value];
  }

  get previewLetterSpacing(): string {
    const spacing: Record<AccessibilityPreferences['letterSpacing'], string> = {
      standard: 'normal',
      wide: '0.04em',
      wider: '0.08em',
    };
    return spacing[this.form.controls.letterSpacing.value];
  }

  get previewLineHeight(): string {
    const spacing: Record<AccessibilityPreferences['lineSpacing'], string> = {
      standard: '1.5',
      relaxed: '1.75',
      wide: '1.95',
    };
    return spacing[this.form.controls.lineSpacing.value];
  }

  back(): void {
    this.step.update((value) => Math.max(0, value - 1));
  }

  next(): void {
    if (this.step() === 0 && !this.form.controls.name.valid) {
      this.form.controls.name.markAsTouched();
      return;
    }
    if (this.step() < 3) {
      this.step.update((value) => value + 1);
      return;
    }
    this.save();
  }

  save(): void {
    if (this.step() !== 3 || !this.form.valid) return;
    const values = this.form.getRawValue();
    const profile: LearnerProfile = {
      ...this.users.profile(),
      name: values.name.trim(),
      ageGroup: values.ageGroup,
      learningGoals: [values.goal],
      interests: values.interests,
      preferences: {
        ...this.users.profile().preferences,
        readingFont: values.readingFont,
        fontSize: values.fontSize,
        letterSpacing: values.letterSpacing,
        lineSpacing: values.lineSpacing,
        theme: values.theme,
        textToSpeech: values.textToSpeech,
        currentLineHighlight: values.currentLineHighlight,
        reducedClutter: values.reducedClutter,
      },
    };
    this.users.save(profile);
    void this.router.navigate(['/assessment']);
  }
}
