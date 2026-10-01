import { DOCUMENT } from '@angular/common';
import { Inject, inject, Injectable, signal } from '@angular/core';
import { Achievement } from '../models/achievement.model';
import { Activity } from '../models/activity.model';
import { Exercise} from '../models/exercise.model';
import { LearnerProfile } from '../models/learner-profile.model';
import { Progress } from '../models/progress.model';
import { User } from '../models/user.model';
import { ExerciseAttempt } from '../models/exercise-attempt.model';
import { AccessibilityPreferences } from '../models/accessibility-preferences.model';

export const API_BASE_URL = '/api';
export const API_ENDPOINTS = {
  login: `${API_BASE_URL}/auth/login/`,
  register: `${API_BASE_URL}/auth/register/`,
  profile: `${API_BASE_URL}/profile/`,
  assessment: `${API_BASE_URL}/assessment/`,
  assessmentAttempt: `${API_BASE_URL}/assessment/attempt/`,
  nextExercise: `${API_BASE_URL}/exercises/next/`,
  exerciseAttempt: `${API_BASE_URL}/exercises/attempt/`,
  progress: `${API_BASE_URL}/progress/`,
  nextRealWorld: `${API_BASE_URL}/real-world/next/`,
} as const;

const defaultProfile: LearnerProfile = {
  name: 'Alex',
  ageGroup: '16–18',
  learningGoals: ['Reading faster', 'Understanding texts'],
  interests: ['Music', 'Stories', 'Space'],
  currentFocus: 'Reading fluency',
  preferences: {
    readingFont: 'default',
    fontSize: 'comfortable',
    letterSpacing: 'standard',
    lineSpacing: 'relaxed',
    textToSpeech: false,
    currentLineHighlight: true,
    reducedClutter: false,
    theme: 'light',
  },
};

const exercises: Exercise[] = [
  {
    id: 201,
    type: 'reading_fluency',
    skill: 'Reading fluency',
    difficulty: 2,
    content: {
      prompt: 'Which word completes the sentence?\nThe bright stars filled the night ___.',
      options: ['sky', 'key', 'shy'],
      correctAnswer: 'sky',
      explanation: 'You found the word that makes the sentence complete.',
      instruction: 'Take your time. Read each option and choose the one that fits.',
    },
  },
  {
    id: 202,
    type: 'decoding',
    skill: 'Decoding',
    difficulty: 2,
    content: {
      prompt: 'Which word rhymes with “train”?',
      options: ['brain', 'stone', 'bright'],
      correctAnswer: 'brain',
      explanation: '“Brain” and “train” share the same ending sound.',
    },
  },
  {
    id: 203,
    type: 'comprehension',
    skill: 'Comprehension',
    difficulty: 2,
    content: {
      prompt: 'Maya packed a raincoat before leaving. What might the weather be like?',
      options: ['Rainy', 'Very hot', 'Snowy'],
      correctAnswer: 'Rainy',
      explanation: 'A raincoat is a useful clue that it may rain.',
    },
  },
  {
    id: 204,
    type: 'phoneme_identification',
    skill: 'Sound awareness',
    difficulty: 1,
    content: {
      prompt: 'Which word starts with the same sound as “moon”?',
      options: ['map', 'sun', 'lamp'],
      correctAnswer: 'map',
      explanation: '“Moon” and “map” both start with the /m/ sound.',
    },
  },
  {
    id: 205,
    type: 'rapid_naming',
    skill: 'Word recognition',
    difficulty: 2,
    content: {
      prompt: 'Choose the word you see here:  garden',
      options: ['garden', 'golden', 'gather'],
      correctAnswer: 'garden',
      explanation: 'You matched the word by noticing its letters.',
    },
  },
  {
    id: 206,
    type: 'phoneme_manipulation',
    skill: 'Sound awareness',
    difficulty: 2,
    content: {
      prompt: 'Change the first sound in “cat” to /h/. What word do you make?',
      options: ['hat', 'hot', 'had'],
      correctAnswer: 'hat',
      explanation: 'Changing /k/ to /h/ makes the word “hat”.',
    },
  },
];

const realWorldExercise: Exercise = {
  id: 301,
  type: 'comprehension',
  skill: 'Everyday reading',
  difficulty: 2,
  content: {
    prompt: 'Which platform should you go to?',
    options: ['Platform 2', 'Platform 3', 'Platform 4', 'Platform 5'],
    correctAnswer: 'Platform 4',
    explanation: 'The travel board lists Platform 4 for the 08:35 bus.',
  },
};

const defaultProgress: Progress = {
  exercisesCompleted: 24,
  currentStreak: 4,
  skills: [
    { id: 1, name: 'Reading fluency', progress: 58, change: 13 },
    { id: 2, name: 'Decoding', progress: 68, change: 11 },
    { id: 3, name: 'Comprehension', progress: 84, change: 4 },
    { id: 4, name: 'Word recognition', progress: 72, change: 8 },
  ],
  achievements: [
    { id: 1, title: 'Finding your rhythm', description: 'Practiced 3 days in a row', icon: '✳' },
    { id: 2, title: 'A curious mind', description: 'Completed 20 activities', icon: '↗' },
  ],
};

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly authenticated = signal(true);
  readonly isAuthenticated = this.authenticated.asReadonly();

  login(_email: string, _password: string): void {
    this.authenticated.set(true);
  }

  register(name: string, email: string): void {
    this.authenticated.set(true);
    this.user.update((user) => ({
      ...user,
      name,
      email,
      assessmentCompleted: false,
      profile: { ...user.profile, name },
    }));
  }

  completeAssessment(): void {
    this.user.update((user) => ({ ...user, assessmentCompleted: true }));
  }

  logout(): void {
    this.authenticated.set(false);
  }

  private readonly user = signal<User>({
    id: 1,
    name: defaultProfile.name,
    email: 'alex@example.com',
    assessmentCompleted: false,
    profile: defaultProfile,
  });

  get currentUser(): User {
    return this.user();
  }

  updateProfile(profile: LearnerProfile): void {
    this.user.update((user) => ({ ...user, name: profile.name, profile }));
  }
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly learner = signal(defaultProfile);
  readonly profile = this.learner.asReadonly();
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

@Injectable({ providedIn: 'root' })
export class ExerciseService {
  private index = 0;

  nextExercise(): Exercise {
    const exercise = exercises[this.index % exercises.length];
    this.index += 1;
    return exercise;
  }

  assessmentExercises(): Exercise[] {
    return exercises;
  }

  realWorldExercise(): Exercise {
    return realWorldExercise;
  }

  nextActivity(): Activity {
    return {
      id: 1,
      type: 'exercise',
      skill: 'Reading fluency',
      title: 'Words in a sentence',
      description: 'Build confidence spotting familiar words in context.',
      estimatedMinutes: 5,
      difficulty: 2,
      reason:
        'You’ve been practicing reading fluency, so this activity helps you recognize common words more quickly.',
    };
  }
}

@Injectable({ providedIn: 'root' })
export class AssessmentService {
  private readonly exerciseService = inject(ExerciseService);
  private readonly progressService = inject(ProgressService);

  getAssessment(): Exercise[] {
    return this.exerciseService.assessmentExercises();
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.progressService.recordAttempt(attempt, skill);
  }
}

@Injectable({ providedIn: 'root' })
export class RealWorldService {
  private readonly exerciseService = inject(ExerciseService);
  private readonly progressService = inject(ProgressService);

  nextScenario(): Exercise {
    return this.exerciseService.realWorldExercise();
  }

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.progressService.recordAttempt(attempt, skill);
  }
}

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private readonly currentProgress = signal<Progress>(defaultProgress);
  readonly progress = this.currentProgress.asReadonly();

  recordAttempt(attempt: ExerciseAttempt, skill: string): void {
    this.currentProgress.update((progress) => ({
      ...progress,
      exercisesCompleted: progress.exercisesCompleted + 1,
      skills: progress.skills.map((item) =>
        item.name === skill
          ? { ...item, progress: attempt.correct ? Math.min(100, item.progress + 2) : item.progress }
          : item,
      ),
    }));
  }

  addAchievement(achievement: Achievement): void {
    this.currentProgress.update((progress) => ({
      ...progress,
      achievements: [...progress.achievements, achievement],
    }));
  }
}
