from __future__ import annotations

import re

from app.ai.llm_service import llm_service
from app.ai.prompt_templates import QUESTION_GENERATION_PROMPT
from app.ai.question_planner import build_question_blueprints, build_role_context
from app.schemas import GeneratedQuestion


async def generate_questions(
    job_description: str,
    count: int = 5,
    role_title: str | None = None,
    skills: list[str] | str | None = None,
) -> list[GeneratedQuestion]:
    count = max(1, min(count, 20))
    context = await build_role_context(role_title or _guess_title(job_description), skills, job_description)
    fallback = build_question_blueprints(context, count)
    prompt = QUESTION_GENERATION_PROMPT.format(
        job_description=job_description,
        role_title=context.title,
        role_domain=context.domain,
        skills=", ".join(context.skills) or "Not specified",
        live_context="\n".join(f"- {item}" for item in context.live_context) or "No live research snippets available.",
        count=count,
    )
    raw_questions = await llm_service.generate_json(prompt, fallback=fallback)
    if isinstance(raw_questions, dict):
        raw_questions = raw_questions.get("questions", [])
    if not isinstance(raw_questions, list):
        raw_questions = []

    validated: list[GeneratedQuestion] = []
    for item in raw_questions[:count]:
        if not isinstance(item, dict):
            continue
        try:
            validated.append(GeneratedQuestion(**item))
        except (TypeError, ValueError):
            continue
    if len(validated) < count:
        existing_text = {question.text for question in validated}
        for item in fallback:
            if item["text"] in existing_text:
                continue
            validated.append(GeneratedQuestion(**item))
            if len(validated) == count:
                break
    return validated[:count]


def _guess_title(job_description: str) -> str:
    first_line = job_description.strip().splitlines()[0] if job_description.strip() else "Role"
    title_match = re.match(r"^(?:#+\s*)?(.*?)(?:\s*[-:|].*)?$", first_line)
    if title_match:
        candidate = title_match.group(1).strip()
        if candidate and len(candidate) <= 80:
            return candidate
    return "Role"
