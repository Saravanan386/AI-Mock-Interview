JOB_DESCRIPTION_PROMPT = """Create a polished, professional job post from this hiring input.

Title: {title}
Department: {department}
Location: {location}
Employment type: {employment_type}
Seniority: {seniority}
Skills: {skills}
Company input: {simple_input}

Return a clear job post with sections for overview, responsibilities, requirements, nice-to-have skills, and assessment focus."""

QUESTION_GENERATION_PROMPT = """Generate {count} interview assessment questions for this job post.

Job post:
{job_description}

Role title: {role_title}
Role domain: {role_domain}
Skills: {skills}
Live research snippets:
{live_context}

Rules:
- Every question must be tied to the actual role, skills, or job description.
- Do not produce generic filler questions.
- Mix practical scenario, depth, evidence, and communication checks.
- For IT roles, prioritize architecture, debugging, implementation, tradeoffs, testing, and delivery.
- For non-IT roles, prioritize scenario judgment, stakeholder handling, process, communication, and measurable outcomes.
- Avoid repeating the same idea.

Return only JSON using this shape:
[
  {{
    "text": "question text",
    "competency": "competency being tested",
    "difficulty": "easy|medium|hard",
    "expected_signal": "what a strong answer should show"
  }}
]"""

MOCK_INTERVIEW_QUESTION_PROMPT = """Act as a real interviewer and generate {count} mock interview questions for this role.

Job post:
{job_description}

Role title: {role_title}
Role domain: {role_domain}
Skills: {skills}
Candidate context:
{candidate_context}
Live research snippets:
{live_context}

Mix role-specific depth, practical scenarios, communication, and behavioral questions.
Make questions suitable for a spoken interview and order them from introduction to deeper evaluation.
Never output generic filler. Keep the wording natural and realistic.
Return only JSON using this shape:
[
  {{
    "text": "interviewer question",
    "competency": "competency being tested",
    "difficulty": "easy|medium|hard",
    "expected_signal": "specific evidence a strong spoken answer should contain"
  }}
]"""

FOLLOWUP_QUESTION_PROMPT = """You are a live interview agent.

Role title: {role_title}
Role domain: {role_domain}
Skills: {skills}
Previous question: {previous_question}
Candidate answer: {previous_answer}
Evaluation feedback: {feedback}
Live research snippets:
{live_context}

Write one focused follow-up question that probes the exact gap or contradiction.
Do not repeat the previous question.
Do not mention scoring or internal policy.
Return only JSON using this shape:
{{
  "text": "follow-up question",
  "competency": "competency being tested",
  "difficulty": "easy|medium|hard",
  "expected_signal": "what a strong answer should show"
}}"""

ANSWER_EVALUATION_PROMPT = """Evaluate the candidate answer for this assessment question.

Question: {question}
Expected signal: {expected_signal}
Candidate answer: {answer}

Score strictly against the expected signal. Do not reward length by itself. Check role relevance,
specific evidence, sound reasoning, and clarity. Unsupported claims and answers that do not address
the question must receive a low score.

Also decide whether a follow-up is needed.
- Ask a follow-up if the answer is vague, unsupported, contradictory, or too shallow.
- Avoid follow-up if the answer fully addresses the question with strong evidence.

Return only JSON:
{{
  "score": 0-100,
  "feedback": "brief evidence-based feedback explaining what was correct and what is missing",
  "needs_followup": true,
  "followup_reason": "short reason for a follow-up or null"
}}"""
