Real-life daily exercises
=========================

Setup:

    python manage.py migrate
    python manage.py load_real_life_exercises

The importer defaults to `Exercises-AI/real_life_exercises.json`, copied from the
provided age-group scenario bank. An optional path imports another bank with the
same `{"age_groups": {"under_12": [exercise, ...], ...}}` structure. Imports validate
every row before writing and update existing exercise IDs without deleting history.
The bundled bank uses the single-answer scenarios from `frontend/src/app/core/data/IRL_SCENARIO.json`.
Its `18_plus` label is mapped to the backend profile value `19_plus` during import.
There are currently only three scenarios per group, so daily sets repeat until
more scenarios are imported.

Authenticated API:

- `GET /api/assessments/real_life/daily/` assigns and returns the same three
  age-appropriate exercises throughout a calendar day. Each entry has an
  `attempt_id`, an `exercise` in the supplied JSON shape (without `correct_answer`),
  and completion/result fields. The response includes `completed`, `remaining`,
  `locked`, and `next_available_at`. Completed exercises remain visible as history;
  they cannot be replaced with new exercises that day.
- `POST /api/assessments/real_life/<attempt_id>/complete/` with
  `{"answer": "Get ready to leave"}` records completion and correctness.
  Wrong answers also count as completed. Retries return the original saved result.
  Other users' attempts return 404; unfinished past-day attempts return 409.
  The top-level `correct_answer` is revealed only for completed attempts so the
  frontend can display feedback; it is null for unfinished attempts.

The day resets at midnight in `REAL_LIFE_TIME_ZONE` (default `Europe/Athens`),
independently of the server timezone. Yesterday's unfinished assignments expire.
New sets prefer exercises least recently assigned; a finite bank eventually repeats.
Each age group needs at least three imported exercises.

User-row locking serializes assignment and completion on PostgreSQL. Database
constraints restrict each user to three distinct slots/exercises per date. Exercise
snapshots preserve the original content and expected answer in completion records.

The existing AI generation endpoint `POST /api/assessments/real_life/` remains a
separate legacy flow. The real-life frontend page uses the daily API, resumes the
first unfinished scenario, saves each answer before showing feedback, and prevents
replaying completed scenarios. After the third completion it displays the next
unlock time. Refreshing the page reloads authoritative completion status.

Tests: `python manage.py test assessments.test_real_life`

Focused frontend tests (from `frontend`):

    npm test -- --watch=false --ts-config tsconfig.real-life-test.json --include "**/real-world*.spec.ts"

This separate test configuration avoids unrelated existing test compilation errors
in `service-connections.spec.ts` while exercising the daily API integration.
