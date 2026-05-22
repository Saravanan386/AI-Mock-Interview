from app.ai.llm_service import llm_service
from app.ai.prompt_templates import ANSWER_EVALUATION_PROMPT
from app.schemas import EvaluateAnswerResponse


async def evaluate_answer(question: str, answer: str, expected_signal: str | None = None) -> EvaluateAnswerResponse:
    fallback_score = _fallback_score(answer, expected_signal)
    fallback = {
        "score": fallback_score,
        "feedback": _fallback_feedback(fallback_score),
        "needs_followup": fallback_score < 72.0,
        "followup_reason": _fallback_followup_reason(fallback_score, answer),
    }
    prompt = ANSWER_EVALUATION_PROMPT.format(
        question=question,
        expected_signal=expected_signal or "No explicit expected signal was provided.",
        answer=answer,
    )
    data = await llm_service.generate_json(prompt, fallback=fallback)
    if not isinstance(data, dict):
        data = fallback
    score = _coerce_score(data.get("score"), fallback_score)
    feedback = str(data.get("feedback") or fallback["feedback"]).strip()
    needs_followup = _coerce_bool(data.get("needs_followup"), fallback=score < 72.0)
    followup_reason = data.get("followup_reason")
    if followup_reason is None and needs_followup:
        followup_reason = _fallback_followup_reason(score, answer)
    return EvaluateAnswerResponse(
        score=score,
        feedback=feedback[:2000],
        needs_followup=needs_followup,
        followup_reason=str(followup_reason).strip()[:1000] if followup_reason else None,
    )


def _coerce_score(value: object, fallback: float) -> float:
    try:
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        score = fallback
    return round(max(0.0, min(100.0, score)), 2)


def _fallback_score(answer: str, expected_signal: str | None = None) -> float:
    """Deterministic rubric used only when the configured LLM is unavailable."""
    words = [word.strip(".,:;!?()[]").lower() for word in answer.split() if word.strip()]
    if not words:
        return 0.0

    length_score = min(35.0, len(words) * 0.7)
    evidence_markers = {"because", "result", "improved", "reduced", "increased", "measured", "example", "outcome"}
    reasoning_score = min(25.0, len(set(words) & evidence_markers) * 5.0)
    numeric_evidence = any(any(character.isdigit() for character in word) for word in words)
    evidence_score = 15.0 if numeric_evidence else 5.0

    expected_words = {
        word.strip(".,:;!?()[]").lower()
        for word in (expected_signal or "").split()
        if len(word.strip(".,:;!?()[]")) > 4
    }
    overlap = len(set(words) & expected_words) / max(1, len(expected_words))
    relevance_score = min(25.0, overlap * 100.0)
    return round(min(100.0, length_score + reasoning_score + evidence_score + relevance_score), 2)


def _fallback_feedback(score: float) -> str:
    if score >= 80:
        return "Strong answer with enough detail to evaluate experience and judgment."
    if score >= 60:
        return "Reasonable answer, but more concrete examples and outcomes would improve confidence."
    return "Answer is too brief; add specific context, actions, tradeoffs, and results."


def _fallback_followup_reason(score: float, answer: str) -> str:
    if not answer.strip():
        return "The answer was empty and needs clarification."
    if score >= 72:
        return "The answer is strong, but the interviewer can still probe for deeper evidence."
    if score >= 45:
        return "The answer needs more concrete evidence and a clearer example."
    return "The answer is too weak or too vague for a confident evaluation."


def _coerce_bool(value: object, fallback: bool = False) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return fallback
