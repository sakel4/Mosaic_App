import { LearnerProfile } from './learner-profile.model';

export interface User {
  id: number;
  name: string;
  email: string;
  assessmentCompleted: boolean;
  profile: LearnerProfile;
}
