from __future__ import annotations

from app.ai.llm_service import llm_service
from app.ai.prompt_templates import FOLLOWUP_QUESTION_PROMPT, MOCK_INTERVIEW_QUESTION_PROMPT
from app.ai.question_planner import RoleContext, build_question_blueprints, build_role_context, build_turn_question
from app.schemas import GeneratedQuestion


async def generate_first_mock_question(
    job_description: str,
    *,
    role_title: str | None = None,
    skills: list[str] | str | None = None,
    candidate_context: str | None = None,
) -> GeneratedQuestion:
    context = await build_role_context(role_title or "Role", skills, job_description)
    return await generate_turn_question(
        context,
        turn_index=0,
        asked_texts=set(),
        asked_competencies=[],
        candidate_context=candidate_context,
    )


async def generate_turn_question(
    context: RoleContext,
    *,
    turn_index: int,
    asked_texts: set[str],
    asked_competencies: list[str],
    previous_question: str | None = None,
    previous_answer: str | None = None,
    feedback: str | None = None,
    candidate_context: str | None = None,
) -> GeneratedQuestion:
    if previous_question and previous_answer:
        fallback = build_turn_question(
            context,
            turn_index,
            asked_texts=asked_texts,
            asked_competencies=asked_competencies,
            previous_question=previous_question,
            previous_answer=previous_answer,
            followup_reason=feedback,
        )
        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            role_title=context.title,
            role_domain=context.domain,
            skills=", ".join(context.skills) or "Not specified",
            previous_question=previous_question,
            previous_answer=previous_answer,
            feedback=feedback or "Need a deeper probe",
            live_context="\n".join(f"- {item}" for item in context.live_context) or "No live research snippets available.",
        )
        raw = await llm_service.generate_json(prompt, fallback=fallback)
        return _coerce_question(raw, fallback)

    fallback = build_turn_question(
        context,
        turn_index,
        asked_texts=asked_texts,
        asked_competencies=asked_competencies,
    )
    prompt = MOCK_INTERVIEW_QUESTION_PROMPT.format(
        job_description=context.description,
        role_title=context.title,
        role_domain=context.domain,
        skills=", ".join(context.skills) or "Not specified",
        candidate_context=candidate_context or "No candidate context supplied.",
        live_context="\n".join(f"- {item}" for item in context.live_context) or "No live research snippets available.",
        count=1,
    )
    raw = await llm_service.generate_json(prompt, fallback=[fallback])
    if isinstance(raw, list) and raw:
        return _coerce_question(raw[0], fallback)
    if isinstance(raw, dict):
        return _coerce_question(raw, fallback)
    return _coerce_question(fallback, fallback)


async def generate_mock_interview_questions(
    job_description: str,
    count: int = 5,
    role_title: str | None = None,
    skills: list[str] | str | None = None,
    candidate_context: str | None = None,
) -> list[GeneratedQuestion]:
    context = await build_role_context(role_title or "Role", skills, job_description)
    fallback = build_question_blueprints(context, count)
    prompt = MOCK_INTERVIEW_QUESTION_PROMPT.format(
        job_description=job_description,
        role_title=context.title,
        role_domain=context.domain,
        skills=", ".join(context.skills) or "Not specified",
        candidate_context=candidate_context or "No candidate context supplied.",
        live_context="\n".join(f"- {item}" for item in context.live_context) or "No live research snippets available.",
        count=count,
    )
    raw = await llm_service.generate_json(prompt, fallback=fallback)
    if isinstance(raw, dict):
        raw = raw.get("questions", [])
    if not isinstance(raw, list):
        raw = []

    questions: list[GeneratedQuestion] = []
    for item in raw[:count]:
        if not isinstance(item, dict):
            continue
        try:
            question = GeneratedQuestion(**item)
        except (TypeError, ValueError):
            continue
        if question.text not in {existing.text for existing in questions}:
            questions.append(question)
    if len(questions) < count:
        existing_text = {question.text for question in questions}
        for item in fallback:
            if item["text"] in existing_text:
                continue
            questions.append(GeneratedQuestion(**item))
            if len(questions) == count:
                break
    return questions[:count]


def _coerce_question(raw: object, fallback: dict[str, str]) -> GeneratedQuestion:
    candidate = raw if isinstance(raw, dict) else fallback
    try:
        return GeneratedQuestion(**candidate)
    except (TypeError, ValueError):
        return GeneratedQuestion(**fallback)
