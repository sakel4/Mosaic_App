export type LearnerInterest =
  | 'Animals'
  | 'Art & crafts'
  | 'Books & stories'
  | 'Cooking & food'
  | 'Dance'
  | 'Games & puzzles'
  | 'Music'
  | 'Nature'
  | 'Science & space'
  | 'Sports'
  | 'Technology'
  | 'Travel';

export const LEARNER_INTERESTS = [
  'Animals',
  'Art & crafts',
  'Books & stories',
  'Cooking & food',
  'Dance',
  'Games & puzzles',
  'Music',
  'Nature',
  'Science & space',
  'Sports',
  'Technology',
  'Travel',
] as const satisfies readonly LearnerInterest[];

export function normalizeLearnerInterests(interests: readonly string[]): LearnerInterest[] {
  const normalized = interests.map((interest) => {
    const value = interest.trim().toLocaleLowerCase();
    if (value === 'stories') return 'Books & stories';
    if (value === 'space') return 'Science & space';
    return LEARNER_INTERESTS.find((option) => option.toLocaleLowerCase() === value);
  });

  return LEARNER_INTERESTS.filter((interest) => normalized.includes(interest));
}
