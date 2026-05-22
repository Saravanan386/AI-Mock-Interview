from app.ai.llm_service import llm_service
from app.ai.prompt_templates import JOB_DESCRIPTION_PROMPT
from app.schemas import JobCreate


async def generate_job_description(payload: JobCreate) -> str:
    skills = ", ".join(payload.skills) if payload.skills else "Not specified"
    fallback = f"""## {payload.title}

### Overview
{payload.simple_input}

### Responsibilities
- Deliver high-quality work aligned with the role requirements.
- Collaborate with team members and communicate progress clearly.
- Apply relevant skills: {skills}.

### Requirements
- Practical experience for a {payload.seniority or "relevant"} level role.
- Strong problem-solving, ownership, and communication skills.

### Assessment Focus
Candidates should demonstrate technical depth, structured thinking, and role-specific judgment."""
    prompt = JOB_DESCRIPTION_PROMPT.format(
        title=payload.title,
        department=payload.department or "Not specified",
        location=payload.location or "Not specified",
        employment_type=payload.employment_type or "Not specified",
        seniority=payload.seniority or "Not specified",
        skills=skills,
        simple_input=payload.simple_input,
    )
    return await llm_service.generate_text(prompt, fallback=fallback)
