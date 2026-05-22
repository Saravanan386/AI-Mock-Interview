from app.models import Answer


def generate_report_summary(answers: list[Answer], overall_score: float) -> dict[str, str]:
    strongest = sorted(
        [answer for answer in answers if answer.score is not None],
        key=lambda answer: answer.score or 0,
        reverse=True,
    )
    weakest = list(reversed(strongest))

    summary = (
        f"Candidate completed {len(answers)} answers with an overall score of {overall_score:.2f}. "
        "Review individual feedback before making a final hiring decision."
    )
    strengths = _join_feedback(strongest[:2], "No clear strengths were identified from the submitted answers.")
    gaps = _join_feedback(weakest[:2], "More evidence is needed to identify specific development gaps.")
    return {"summary": summary, "strengths": strengths, "gaps": gaps}


def _join_feedback(answers: list[Answer], empty: str) -> str:
    items = [answer.evaluation_feedback for answer in answers if answer.evaluation_feedback]
    return " ".join(items) if items else empty
