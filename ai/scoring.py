
import re


def calculate_lead_score(qualification: dict) -> dict:
    score = 0

    # INTEREST: 20 points
    interest = qualification.get("interest")
    if interest and str(interest).strip():
        score += 20

    # BUDGET: 30 points
    budget = qualification.get("budget")
    if budget and str(budget).strip():
        score += 30

    # TIMELINE: score based on urgency
    timeline = qualification.get("timeline")
    if timeline:
        timeline_text = str(timeline).strip().lower()

        if timeline_text in {
            "immediately", "asap", "this week", "next week"
        }:
            score += 30
        elif timeline_text in {"this month", "within 30 days"}:
            score += 25
        elif timeline_text in {"next month", "within 60 days"}:
            score += 20
        else:
            days_match = re.search(
                r"(?:within\s*)?(\d+)\s*days?", timeline_text
            )
            weeks_match = re.search(
                r"(?:within\s*)?(\d+)\s*weeks?", timeline_text
            )
            months_match = re.search(
                r"(?:within\s*)?(\d+)\s*months?", timeline_text
            )

            if days_match:
                days = int(days_match.group(1))
                if days <= 7:
                    score += 30
                elif days <= 14:
                    score += 25
                elif days <= 30:
                    score += 20
            elif weeks_match:
                weeks = int(weeks_match.group(1))
                if weeks <= 1:
                    score += 30
                elif weeks <= 2:
                    score += 25
                elif weeks <= 4:
                    score += 20
            elif months_match:
                months = int(months_match.group(1))
                if months <= 1:
                    score += 20
                elif months <= 3:
                    score += 10

    # REQUIREMENT: 20 points
    requirement = qualification.get("requirement")
    if requirement and str(requirement).strip():
        score += 20

    # Keep score within 0-100
    score = min(score, 100)

    # TEMPERATURE
    if score >= 80:
        status = "hot"
    elif score >= 50:
        status = "warm"
    else:
        status = "cold"

    return {
        "score": score,
        "status": status,
    }
