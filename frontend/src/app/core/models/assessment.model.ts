export interface AssessmentOption {
  id: string;
  text: string;
}

export interface AssessmentItem {
  id: string;
  audio_prompt?: string;
  prompt?: string;
  grapheme?: string;
  options?: AssessmentOption[];
  correct_option_id?: string;
  word?: string;
  sentence?: string;
  sequence?: string[];
  direction?: 'forward' | 'reverse';
}

export interface AssessmentExercise {
  id?: string | number;
  position: number;
  kind: string;
  skill: string;
  difficulty?: number;
  difficulty_level?: number;
  confidence?: string;
  response_type: 'single_choice_set' | 'spoken' | 'spelling' | 'sequence';
  instruction: string;
  language?: string;
  content_data: {
    items?: AssessmentItem[];
    sections?: { id: string; label: string; items: string[] }[];
    passage_lines?: string[];
    passage?: string[];
    audio_required?: boolean;
    audio_supported?: boolean;
    microphone_required?: boolean;
    target_voice_seconds?: number;
    display_ms_per_digit?: number;
  };
}

export interface AssessmentPayload {
    id?: string;
    created_at?: string;
    age_group: string;
    language: string;
    estimated_duration_seconds: number;
    estimated_voice_duration_seconds?: number;
    type?: string;
    assessment_type?: string;
    excercises?: AssessmentExercise[];
    exercises?: AssessmentExercise[];
}
export type AssessmentResponse = { assessment: AssessmentPayload } | AssessmentPayload | AssessmentPayload[];

/** Prepare a REST response for the exercise component, preserving option IDs. */
export function assessmentExercises(response: AssessmentResponse): AssessmentExercise[] {
  const assessment = Array.isArray(response) ? response[0]
    : 'assessment' in response ? response.assessment : response;
  if (!assessment) return [];
  return [...(assessment.exercises ?? assessment.excercises ?? [])]
    .sort((a, b) => a.position - b.position)
    .map((exercise) => ({ ...exercise, difficulty: exercise.difficulty_level ?? exercise.difficulty,
      language: exercise.language ?? assessment.language }));
}
