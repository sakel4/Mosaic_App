import { Exercise } from '../models/exercise.model';
import { LearnerProfile } from '../models/learner-profile.model';
import { Progress } from '../models/progress.model';

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

export const defaultProfile: LearnerProfile = {
  name: '',
  ageGroup: '',
  learningGoals: [],
  interests: [],
  currentFocus: [],
  preferences: {
    readingFont: 'default',
    fontSize: 'comfortable',
    letterSpacing: 'standard',
    lineSpacing: 'standard',
    textToSpeech: false,
    currentLineHighlight: true,
    reducedClutter: false,
    theme: 'light',
  },
};

export const exercises: Exercise[] = [
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

export const realWorldExercise: Exercise = {
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

export const defaultProgress: Progress = {
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
