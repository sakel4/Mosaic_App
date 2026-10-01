import { Injectable } from '@angular/core';
import { Exercise } from '../models/exercise.model';
import { Activity } from '../models/activity.model';
import { exercises, realWorldExercise } from './dummy_data';

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
