import { Exercise } from './exercise.model';

export interface RealWorldScenario {
  id: string;
  title: string;
  context: string;
  information: string[];
  exercise: Exercise;
}
