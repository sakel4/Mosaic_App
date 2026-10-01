import { ExerciseContent } from './exercise-content.model';
import { ExerciseType } from './exercise-type.model';

export interface Exercise {
  id: number;
  type: ExerciseType;
  skill: string;
  difficulty: number;
  language?: string;
  content: ExerciseContent;
}
