from app.models import Answer


def calculate_overall_score(answers: list[Answer]) -> float:
    scores = [answer.score for answer in answers if answer.score is not None]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)


def recommendation_for(score: float) -> str:
    if score >= 85:
        return "strong_hire"
    if score >= 70:
        return "hire"
    if score >= 55:
        return "consider"
    return "do_not_advance"


def calculate_career_score(assessment_score: float, mock_interview_score: float) -> float:
    return round((assessment_score * 0.6) + (mock_interview_score * 0.4), 2)
