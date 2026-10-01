import { UserService } from '../../core/services/user-service';
import { normalizeLearnerInterests } from '../../core/models/learner-interest.model';
import { Component, inject } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AccessibilityPreferences } from '../../core/models/accessibility-preferences.model';
import { LearnerInterest } from '../../core/models/learner-interest.model';
import { LearnerProfile } from '../../core/models/learner-profile.model';
import { ReadingFont } from '../../core/models/reading-font.model';
import { LEARNER_INTERESTS } from '../../core/models/learner-interest.model';
import { InterestPickerComponent } from '../../shared/components/interest-picker-component/interest-picker-component';
import { AuthService } from '../../core/services/auth-service';

@Component({
  imports: [ReactiveFormsModule, InterestPickerComponent],
  selector: 'app-profile',
  styleUrl: './profile.scss',
  templateUrl: './profile.html',
})
export class Profile {
  private readonly auth = inject(AuthService);
  private readonly users = inject(UserService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly afterAssessment = this.route.snapshot.queryParamMap.get('afterAssessment') === 'true';
  readonly interestOptions = LEARNER_INTERESTS;
  saved = false;
  readonly form = new FormGroup({
    name: new FormControl(this.users.profile().name, {
      nonNullable: true,
      validators: [Validators.required],
    }),
    ageGroup: new FormControl(this.users.profile().ageGroup, { nonNullable: true }),
    goal: new FormControl(this.users.profile().learningGoals[0] ?? 'General reading support', {
      nonNullable: true,
    }),
    interests: new FormControl<LearnerInterest[]>(
      normalizeLearnerInterests(this.users.profile().interests),
      { nonNullable: true },
    ),
    readingFont: new FormControl<ReadingFont>(this.users.profile().preferences.readingFont, {
      nonNullable: true,
    }),
    fontSize: new FormControl<AccessibilityPreferences['fontSize']>(
      this.users.profile().preferences.fontSize,
      { nonNullable: true },
    ),
    letterSpacing: new FormControl<AccessibilityPreferences['letterSpacing']>(
      this.users.profile().preferences.letterSpacing,
      { nonNullable: true },
    ),
    lineSpacing: new FormControl<AccessibilityPreferences['lineSpacing']>(
      this.users.profile().preferences.lineSpacing,
      { nonNullable: true },
    ),
    textToSpeech: new FormControl(this.users.profile().preferences.textToSpeech, {
      nonNullable: true,
    }),
    currentLineHighlight: new FormControl(this.users.profile().preferences.currentLineHighlight, {
      nonNullable: true,
    }),
    reducedClutter: new FormControl(this.users.profile().preferences.reducedClutter, {
      nonNullable: true,
    }),
    theme: new FormControl<AccessibilityPreferences['theme']>(
      this.users.profile().preferences.theme,
      { nonNullable: true },
    ),
  });

  get previewFont(): string {
    const fonts: Record<ReadingFont, string> = {
      default: "'DM Sans', sans-serif",
      lexend: "'Lexend', sans-serif",
      opendyslexic: "'OpenDyslexic', sans-serif",
    };
    return fonts[this.form.controls.readingFont.value];
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

  applyFontSize(): void {
    this.users.applyFontSize(this.form.controls.fontSize.value);
  }

  applyReadingFont(): void {
    this.users.applyReadingFont(this.form.controls.readingFont.value);
  }

  save(): void {
    this.form.markAllAsTouched();
    if (!this.afterAssessment && this.form.invalid) return;
    const value = this.form.getRawValue();
    const currentProfile = this.users.profile();
    const preferences: AccessibilityPreferences = {
      readingFont: value.readingFont,
      fontSize: value.fontSize,
      letterSpacing: value.letterSpacing,
      lineSpacing: value.lineSpacing,
      textToSpeech: value.textToSpeech,
      currentLineHighlight: value.currentLineHighlight,
      reducedClutter: value.reducedClutter,
      theme: value.theme,
    };
    const profile: LearnerProfile = this.afterAssessment
      ? {
          ...currentProfile,
          preferences,
        }
      : {
          ...currentProfile,
          name: value.name.trim(),
          ageGroup: value.ageGroup,
          learningGoals: [value.goal],
          interests: value.interests,
          preferences,
        };
    this.users.save(profile);
    if (this.afterAssessment) {
      this.continueToDashboard();
      return;
    }
    this.saved = true;
  }

  continueToDashboard(): void {
    this.users.apply(this.users.profile());
    void this.router.navigate(['/dashboard']);
  }

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}
