# AI Recruitment Platform Backend

FastAPI backend for the company and candidate recruitment workflow.

## Local Stack

- PostgreSQL stores companies, candidates, jobs, questions, assessments, answers, scores, and reports.
- Qdrant indexes generated job posts for semantic retrieval/search.
- LiteLLM can run locally as an OpenAI-compatible gateway at `http://localhost:4000/v1`.

## Run Locally

```powershell
cd backend
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The default local configuration uses SQLite and role-aware deterministic fallbacks, so Docker and a local LLM are not required. To use PostgreSQL/Qdrant, start Docker Desktop, run `docker-compose up -d postgres qdrant`, select the PostgreSQL `DATABASE_URL` shown in `.env.example`, and set `LLM_ENABLED=true` only when an OpenAI-compatible service is listening on port 4000.

To ground interview questions in current web signals, set `LIVE_SEARCH_ENABLED=true`. The service will try to fetch fresh snippets for the selected role and skill mix before generating questions, and it will quietly continue if the search is unavailable.

To verify the registration flow locally:

```powershell
pytest -q tests/test_auth_registration.py
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Complete Candidate-to-Company Workflow

1. `POST /company/register`
2. `POST /company/login`
3. `PUT /company/profile`
4. `POST /jobs/create`
5. `POST /candidate/register`
6. `POST /candidate/login`
7. `GET /roles` - render every open role page (AI Engineer, Data Scientist, and any future company role)
8. `GET /roles/{job_id}` - load one role page without exposing evaluation rubrics
9. `POST /roles/{job_id}/assessment/start`
10. `POST /assessment/answer`
11. `POST /assessment/finish`
12. `POST /roles/{job_id}/mock-interview/start`
13. `POST /mock-interviews/answer`
14. `POST /mock-interviews/finish` - combines assessment (60%) and mock interview (40%)
15. `POST /applications` - apply only to a job returned in the eligible referrals
16. `GET /company/applications`
17. `PATCH /company/applications/{application_id}` - review, shortlist, reject, or hire
18. `POST /company/interviews` - schedule a real company interview round
19. `GET /candidate/interviews`
20. `PATCH /company/interviews/{interview_id}` - complete/cancel the round and record feedback

If the local LLM endpoint is unavailable, the backend returns deterministic development fallbacks so the workflow remains testable.

## Assessment and referral behavior

- Five role-specific questions are generated when a company creates a job.
- `POST /assessment/start` resumes an unfinished attempt instead of creating duplicates.
- Each answer is evaluated against the question's expected signal and returns a 0-100 score plus feedback.
- The expected-answer rubric stays server-side and is not included in candidate assessment question responses.
- Every question must be answered before `POST /assessment/finish` succeeds.
- The assessment result includes its score, feedback, and a next step to complete the mock interview.
- The completed mock interview result includes question-wise feedback, a combined career score, and score-qualified open job referrals.
- Candidates read their own result at `GET /assessment/my-result/{assessment_id}`. Companies use `GET /assessment/result/{assessment_id}` for jobs they own.
- A referral is not an automatic application. `POST /applications` validates ownership, completed attempts, combined score, role relevance, job status, and duplicate applications.
- Companies can see verified assessment/mock scores, control application status, schedule multiple real interview rounds, and return interview feedback.

Job referral score gates are 40 for internships, 50 for entry/fresher roles, 55 for junior, 65 for mid-level, 75 for senior, 82 for lead, and 88 for principal roles. Eligible roles are ranked using 70% combined performance and 30% assessed-role skill/title relevance. Unrelated jobs are not recommended even when the candidate has a high score.

## Frontend page mapping

- Role listing page: `GET /roles`
- AI Engineer (or any selected role) page: `GET /roles/{job_id}`
- Assessment UI: role assessment start plus `/assessment/answer` and `/assessment/finish`
- Mock interview UI: role mock start plus `/mock-interviews/answer` and `/mock-interviews/finish`
- Score/referral page: `GET /mock-interviews/{mock_interview_id}/result`
- Candidate applications page: `GET /applications/me`
- Candidate real interviews page: `GET /candidate/interviews`
- Company hiring dashboard: `GET /company/dashboard`, `/company/applications`, and `/company/interviews`

## Tests

```powershell
pip install -r requirements.txt -r requirements-dev.txt
pytest
```
