The dashboard and both age-specific progress layouts load authenticated statistics
from `GET /api/practice/progress/`. PDF reports use that same saved snapshot.

Totals, streaks, and milestones count stored `ProgressAttempt` records plus completed
`RealLifeExerciseAttempt` records. Real-life completions are read directly, so the
frontend refreshes statistics without submitting a duplicate progress attempt.
Daily history covers 42 calendar days in `REAL_LIFE_TIME_ZONE` (Athens by default).
The current streak may end today or yesterday, and breaks after a missed day.

Practice completions use `POST /api/practice/progress/` with a UUID `client_id`,
`exercise_id`, `skill`, `correct`, and `response_time`. The UUID prevents duplicate
records on retries. `correct: null` records a completed but unscored activity:
it earns a star and contributes to streaks, but is excluded from accuracy.
The frontend retains failed submissions in memory for retry while the app stays
open; navigating to statistics retries them. Account changes clear pending records.

Skill cards distinguish evaluated skill scores (`metric: score`) from practice
accuracy (`metric: accuracy`). Saved profile skill scores take precedence, followed
by personalized-practice baselines, then accuracy from scored outcomes. Score
changes compare against the previous saved evaluation when available. No evaluation
history means zero displayed change. A learner with no recorded activity starts at
zero completed activities; initial assessment scores may still appear in skill cards.
The previously displayed sample totals are not real records and are not imported.

Migration `0005_alter_progressattempt_correct` permits unscored completions.

Backend tests:

    python manage.py test personalized_practice.test_progress

Frontend tests (from `frontend`):

    npm test -- --watch=false --ts-config tsconfig.statistics-test.json --include "src/app/core/services/progress-service.spec.ts" --include "src/app/pages/progress/progress.spec.ts" --include "src/app/pages/dashboard/dashboard.spec.ts" --include "src/app/pages/practice/practice.spec.ts" --include "**/real-world*.spec.ts"

The focused configuration excludes unrelated existing compilation failures in
`service-connections.spec.ts`.
