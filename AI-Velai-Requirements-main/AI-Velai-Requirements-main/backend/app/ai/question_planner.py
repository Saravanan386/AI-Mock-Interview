from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.live_research import fetch_live_research_snippets

IT_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "fastapi",
    "django",
    "flask",
    "api",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "react",
    "next",
    "node",
    "sql",
    "postgres",
    "database",
    "ml",
    "machine learning",
    "llm",
    "rag",
    "data",
    "devops",
    "cloud",
    "azure",
    "aws",
    "gcp",
    "android",
    "ios",
    "testing",
    "automation",
    "cyber",
    "security",
    "software",
    "engineer",
}

NON_IT_KEYWORDS = {
    "sales",
    "marketing",
    "finance",
    "accounting",
    "operations",
    "hr",
    "human resources",
    "teacher",
    "education",
    "nurse",
    "doctor",
    "hospital",
    "customer support",
    "support",
    "logistics",
    "supply chain",
    "project manager",
    "product manager",
    "analyst",
    "designer",
    "content",
    "writer",
    "consultant",
}


@dataclass(slots=True)
class RoleContext:
    title: str
    skills: list[str]
    description: str
    domain: str
    live_context: list[str]


def infer_role_domain(title: str, skills: list[str], description: str) -> str:
    corpus = " ".join([title, description, *skills]).lower()
    it_score = sum(1 for keyword in IT_KEYWORDS if keyword in corpus)
    non_it_score = sum(1 for keyword in NON_IT_KEYWORDS if keyword in corpus)
    if it_score == non_it_score:
        return "it" if any(keyword in corpus for keyword in {"engineer", "developer", "software", "data", "ml", "backend", "frontend"}) else "non_it"
    return "it" if it_score > non_it_score else "non_it"


def normalize_skills(skills: list[str] | str | None) -> list[str]:
    if skills is None:
        return []
    if isinstance(skills, str):
        raw = skills.split(",")
    else:
        raw = skills
    normalized = []
    for skill in raw:
        cleaned = re.sub(r"\s+", " ", str(skill).strip())
        if cleaned and cleaned.lower() not in {item.lower() for item in normalized}:
            normalized.append(cleaned)
    return normalized


async def build_role_context(title: str, skills: list[str] | str | None, description: str) -> RoleContext:
    normalized_skills = normalize_skills(skills)
    domain = infer_role_domain(title, normalized_skills, description)
    search_terms = [title, *normalized_skills[:4], "interview questions", "skills"]
    if domain == "it":
        search_terms.append("system design debugging interview")
    else:
        search_terms.append("scenario based interview communication")
    live_context = await fetch_live_research_snippets(" ".join(search_terms))
    return RoleContext(
        title=title.strip() or "Role",
        skills=normalized_skills,
        description=description.strip(),
        domain=domain,
        live_context=live_context,
    )


def _skill_for_index(skills: list[str], index: int, title: str) -> str:
    if skills:
        return skills[index % len(skills)]
    return title


def build_question_blueprints(context: RoleContext, count: int, *, previous_question: str | None = None, previous_answer: str | None = None, followup_reason: str | None = None) -> list[dict[str, str]]:
    count = max(1, count)
    blueprints: list[dict[str, str]] = []
    archetypes = (
        [
            "walk me through your experience and how it prepares you for {title}",
            "describe how you would apply {skill} in a real project for {title}",
            "explain the most important tradeoff or risk you would consider in this role",
            "tell me about a time you solved a difficult problem with stakeholders or team members",
            "how would you measure success in the first 30 days of this role",
            "if quality and speed conflict, how do you decide what to do first",
        ]
        if context.domain == "it"
        else [
            "walk me through your experience and how it prepares you for {title}",
            "describe how you would apply {skill} in a real work situation for {title}",
            "explain the most important process, risk, or judgment call in this role",
            "tell me about a time you solved a difficult problem with customers, stakeholders, or your team",
            "how would you measure success in the first 30 days of this role",
            "if quality and speed conflict, how do you decide what to do first",
        ]
    )
    deepeners = (
        [
            "what would you do if your first approach failed",
            "how would you validate that the result is actually correct",
            "what would you change if the constraints became tighter",
        ]
        if context.domain == "it"
        else [
            "what would you do if the first approach failed",
            "how would you verify that the outcome is acceptable",
            "what would you change if the constraints became tighter",
        ]
    )

    if previous_question and previous_answer:
        first_skill = _skill_for_index(context.skills, 0, context.title)
        prompt = (
            f"You mentioned {followup_reason or 'a gap'} in your answer. "
            f"Can you walk me through exactly how you handled {first_skill} in {context.title}, "
            f"what you personally did, and what the measurable result was?"
        )
        blueprints.append(
            {
                "text": prompt,
                "competency": first_skill,
                "difficulty": "medium",
                "expected_signal": "clear ownership, concrete actions, evidence, and outcome",
            }
        )
        count -= 1

    for index in range(count):
        skill = _skill_for_index(context.skills, index, context.title)
        archetype = archetypes[index % len(archetypes)]
        if index == 0 and context.live_context:
            text = (
                f"{archetype.format(title=context.title, skill=skill)}. "
                f"Please be specific about {skill}."
            )
        elif index == 1:
            text = f"How have you used {skill} in a real project or business situation, and what changed because of it?"
        elif index == 2:
            text = f"{archetype.format(title=context.title, skill=skill)}. Share the tradeoffs you considered."
        elif index == 3:
            text = f"Tell me about a difficult decision in a role like {context.title} and how you justified it."
        elif index == 4:
            text = f"What would success look like in your first 30 days in {context.title}, and how would you track it?"
        else:
            text = f"If pressure rises and you lose time, how would you protect quality while still delivering in this {context.title} role?"

        expected_signal = (
            f"evidence-based explanation of {skill}, role-relevant context, tradeoffs, and results"
        )
        blueprints.append(
            {
                "text": text,
                "competency": skill,
                "difficulty": "easy" if index == 0 else "medium" if index < 4 else "hard",
                "expected_signal": expected_signal,
            }
        )
    return blueprints


def build_turn_question(
    context: RoleContext,
    turn_index: int,
    *,
    asked_texts: set[str] | None = None,
    asked_competencies: list[str] | None = None,
    previous_question: str | None = None,
    previous_answer: str | None = None,
    followup_reason: str | None = None,
) -> dict[str, str]:
    asked_texts = asked_texts or set()
    asked_competencies = asked_competencies or []

    if previous_question and previous_answer:
        skill = next((item for item in context.skills if item not in asked_competencies), None)
        skill = skill or _skill_for_index(context.skills, turn_index, context.title)
        text = (
            f"{followup_reason or 'I need more detail here'}. "
            f"Can you explain exactly how you handled {skill} in {context.title}, "
            f"what you personally did, and what the measurable result was?"
        )
        return {
            "text": text,
            "competency": skill,
            "difficulty": "medium",
            "expected_signal": "clear ownership, concrete actions, evidence, and outcome",
        }

    skill = next((item for item in context.skills if item not in asked_competencies), None)
    skill = skill or _skill_for_index(context.skills, turn_index, context.title)
    if turn_index == 0:
        text = f"Walk me through your background and explain why it prepares you for {context.title}."
        difficulty = "easy"
    elif turn_index == 1:
        text = f"How have you used {skill} in a real project or work situation, and what changed because of it?"
        difficulty = "medium"
    elif turn_index == 2:
        text = f"What tradeoffs would you consider when applying {skill} in this role?"
        difficulty = "medium"
    elif turn_index == 3:
        text = f"Tell me about a difficult decision you made in a role like {context.title} and how you justified it."
        difficulty = "medium"
    elif turn_index == 4:
        text = f"What would success look like in your first 30 days in {context.title}, and how would you track it?"
        difficulty = "hard"
    else:
        text = f"If pressure rises and time is limited, how would you protect quality while still delivering in this {context.title} role?"
        difficulty = "hard"

    if text in asked_texts:
        text = f"{text} Give a different angle than your earlier answer."

    return {
        "text": text,
        "competency": skill,
        "difficulty": difficulty,
        "expected_signal": f"evidence-based explanation of {skill}, role-relevant context, tradeoffs, and results",
    }
