export interface AssessmentOption {
  id: string;
  text: string;
}

export interface AssessmentItem {
  id: string;
  audio_prompt: string;
  options: AssessmentOption[];
  correct_option_id: string;
}

export interface AssessmentExercise {
  id?: number;
  position: number;
  kind: string;
  skill: string;
  difficulty: number;
  response_type: 'single_choice_set';
  instruction: string;
  language?: string;
  content_data: { items: AssessmentItem[] };
}

export interface AssessmentResponse {
  assessment: {
    age_group: string;
    language: string;
    estimated_duration_seconds: number;
    estimated_voice_duration_seconds?: number;
    type: string;
    excercises?: AssessmentExercise[];
    exercises?: AssessmentExercise[];
  };
}

/** Prepare a REST response for the exercise component, preserving option IDs. */
export function assessmentExercises(response: AssessmentResponse): AssessmentExercise[] {
  const assessment = response.assessment;
  return [...(assessment.exercises ?? assessment.excercises ?? [])]
    .sort((a, b) => a.position - b.position)
    .map((exercise) => ({ ...exercise, language: exercise.language ?? assessment.language }));
}
