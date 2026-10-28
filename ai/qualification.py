
import re


# =========================================================
# HELPER - NORMALIZE TEXT
# =========================================================

def normalize_text(message: str) -> str:
    if not message:
        return ""

    return " ".join(message.lower().strip().split())


# =========================================================
# HELPER - PERSONAL INTEREST
# =========================================================

def has_personal_interest_intent(message: str) -> bool:
    message_lower = normalize_text(message)

    interest_phrases = [
        "i am interested",
        "i'm interested",
        "im interested",
        "i want to learn",
        "i wanna learn",
        "i also want to learn",
        "i also want to study",
        "i also want to do",
        "i also want",
        "i want to study",
        "i want to join",
        "i want to take",
        "i would like to learn",
        "i would like to study",
        "i would like to join",
        "i would like to take",
        "i'm planning to learn",
        "im planning to learn",
        "i am planning to learn",
        "i plan to learn",
        "i'm planning to study",
        "im planning to study",
        "i am planning to study",
        "i plan to study",
        "i want to do",
        "i would like to do",
        "my interest is",
        "my interested course is",
        "i am learning",
        "i'm learning",
        "im learning",
        "teach me",
        "learn about",
        "study about",
    ]

    return any(phrase in message_lower for phrase in interest_phrases)


# =========================================================
# HELPER - BUDGET INTENT
# =========================================================

def has_budget_intent(message: str) -> bool:
    message_lower = normalize_text(message)

    budget_phrases = [
        "my budget",
        "my maximum budget",
        "my max budget",
        "i have a budget",
        "i have budget",
        "i can spend",
        "i could spend",
        "i can afford",
        "i could afford",
        "i am willing to spend",
        "i'm willing to spend",
        "im willing to spend",
        "i am ready to spend",
        "i'm ready to spend",
        "im ready to spend",
        "budget for me",
        "budget is around",
        "budget is about",
        "budget is approximately",
    ]

    return any(phrase in message_lower for phrase in budget_phrases)


# =========================================================
# HELPER - TIMELINE INTENT
# =========================================================

def has_timeline_intent(message: str) -> bool:
    message_lower = normalize_text(message)

    timeline_phrases = [
        "i want to start",
        "i wanna start",
        "i can start",
        "i could start",
        "i would like to start",
        "i'm planning to start",
        "im planning to start",
        "i am planning to start",
        "i plan to start",
        "i need to start",
        "i prefer to start",
        "i am ready to start",
        "i'm ready to start",
        "im ready to start",
        "i will start",
        "i'll start",
        "ill start",
        "i want to begin",
        "i can begin",
        "i would like to begin",
        "i plan to begin",
    ]

    return any(phrase in message_lower for phrase in timeline_phrases)


# =========================================================
# HELPER - REQUIREMENT INTENT
# =========================================================

def has_requirement_intent(message: str) -> bool:
    message_lower = normalize_text(message)

    requirement_phrases = [
        # JOB
        "i need a job",
        "i want a job",
        "i want to get a job",
        "i need to get a job",
        "i would like to get a job",
        "i'm trying to get a job",
        "im trying to get a job",
        "i am trying to get a job",
        "my goal is to get a job",
        "my main goal is to get a job",
        "goal is to get a job",
        "get a job",
        "getting a job",
        "find a job",
        "finding a job",
        "i am looking for a job",
        "i'm looking for a job",
        "im looking for a job",
        "looking for a job",
        "i need this for a job",
        "i want this for a job",
        "i need this course for a job",
        "i want this course for a job",
        "i want job placement",
        "i need job placement",
        "i want placement assistance",
        "i need placement assistance",
        "i am looking for job opportunities",
        "i'm looking for job opportunities",
        "im looking for job opportunities",
        "i want job opportunities",
        "i need job opportunities",
        "i want employment",
        "i need employment",

        # CAREER
        "i want career opportunities",
        "i need career opportunities",
        "i want career growth",
        "i need career growth",
        "i want to build my career",
        "i need to build my career",
        "i want to start my career",
        "i need to start my career",
        "my career goal",
        "my goal is career",

        # CAREER SWITCH
        "i want to switch career",
        "i want to switch careers",
        "i want to switch my career",
        "i need to switch career",
        "i need to switch careers",
        "i need to switch my career",
        "i want a career switch",
        "i need a career switch",
        "i am planning a career switch",
        "i'm planning a career switch",
        "im planning a career switch",
        "i am planning to switch career",
        "i'm planning to switch career",
        "im planning to switch career",
        "for a career switch",
        "for career switch",
        "for switching career",
        "for switching careers",
        "to switch career",
        "to switch careers",
        "to switch my career",
        "career change",
        "change my career",

        # SKILL DEVELOPMENT
        "i want to improve my skills",
        "i need to improve my skills",
        "i want to develop my skills",
        "i need to develop my skills",
        "i want to upgrade my skills",
        "i need to upgrade my skills",
        "i want skill development",
        "i need skill development",
        "improve my skills",
        "develop my skills",
        "upgrade my skills",
        "i want to upskill",
        "i need to upskill",
        "upskill myself",
        "upskill",
    ]

    return any(phrase in message_lower for phrase in requirement_phrases)


# =========================================================
# HELPER - EXTRACT BUDGET
# =========================================================

def extract_budget(message: str):
    message_lower = normalize_text(message)
    cleaned_message = message_lower.replace(",", "")

    # Examples: 20k, 25.5k, 15k to 20k
    k_matches = re.findall(
        r"\b(\d+(?:\.\d+)?)\s*k\b",
        cleaned_message,
    )

    if k_matches:
        return max(int(float(value) * 1000) for value in k_matches)

    # Examples: 20 thousand, 25 thousand
    thousand_matches = re.findall(
        r"\b(\d+(?:\.\d+)?)\s*thousand\b",
        cleaned_message,
    )

    if thousand_matches:
        return max(int(float(value) * 1000) for value in thousand_matches)

    # Examples: 20000, 25000, 30000
    number_matches = re.findall(r"\b(\d{4,6})\b", cleaned_message)

    if number_matches:
        return max(int(value) for value in number_matches)

    return None


# =========================================================
# HELPER - EXTRACT MULTIPLE INTERESTS
# =========================================================

def extract_interests(message: str) -> list:
    message_lower = normalize_text(message)

    if not has_personal_interest_intent(message):
        return []

    interest_patterns = [
        ("DevOps", r"\bdev\s*ops\b"),
        ("Azure", r"\bazure\b"),
        ("AWS", r"\baws\b"),
        ("Python", r"\bpython\b"),
        (
            "Cloud Computing",
            r"\bcloud\s+computing\b|\bcloud\s+engineering\b|\bcloud\b",
        ),
    ]

    detected = []

    for interest, pattern in interest_patterns:
        if re.search(pattern, message_lower):
            if interest.casefold() not in {
                item.casefold() for item in detected
            }:
                detected.append(interest)

    return detected


# =========================================================
# QUALIFY LEAD
# =========================================================

def qualify_lead(message: str) -> dict:
    message_lower = normalize_text(message)

    qualification = {
        "interest": None,
        "budget": None,
        "timeline": None,
        "requirement": None,
    }

    # INTEREST
    interests = extract_interests(message)

    if interests:
        qualification["interest"] = ", ".join(interests)

    # BUDGET
    if has_budget_intent(message):
        budget = extract_budget(message)

        if budget is not None:
            qualification["budget"] = budget

    # TIMELINE
    if has_timeline_intent(message):
        if (
            "immediately" in message_lower
            or "right now" in message_lower
            or "start now" in message_lower
            or "begin now" in message_lower
            or "as soon as possible" in message_lower
            or "asap" in message_lower
        ):
            qualification["timeline"] = "Immediately"

        elif "this week" in message_lower:
            qualification["timeline"] = "This week"

        elif "next week" in message_lower:
            qualification["timeline"] = "Next week"

        elif "this month" in message_lower:
            qualification["timeline"] = "This month"

        elif "next month" in message_lower:
            qualification["timeline"] = "Next month"

        else:
            days_match = re.search(
                r"\bwithin\s+(\d{1,2})\s+days?\b",
                message_lower,
            )

            weeks_match = re.search(
                r"\bwithin\s+(\d{1,2})\s+weeks?\b",
                message_lower,
            )

            months_match = re.search(
                r"\bwithin\s+(\d{1,2})\s+months?\b",
                message_lower,
            )

            if days_match:
                days = int(days_match.group(1))
                qualification["timeline"] = (
                    f"Within {days} {'day' if days == 1 else 'days'}"
                )

            elif weeks_match:
                weeks = int(weeks_match.group(1))
                qualification["timeline"] = (
                    f"Within {weeks} {'week' if weeks == 1 else 'weeks'}"
                )

            elif months_match:
                months = int(months_match.group(1))
                qualification["timeline"] = (
                    f"Within {months} {'month' if months == 1 else 'months'}"
                )

    # REQUIREMENT
    if has_requirement_intent(message):
        career_switch_phrases = [
            "career switch",
            "switch career",
            "switch careers",
            "switch my career",
            "switching career",
            "switching careers",
            "career change",
            "change my career",
        ]

        skill_phrases = [
            "improve my skills",
            "skill development",
            "develop my skills",
            "upgrade my skills",
            "upskill",
        ]

        if any(phrase in message_lower for phrase in career_switch_phrases):
            qualification["requirement"] = "Career switch"

        elif any(phrase in message_lower for phrase in skill_phrases):
            qualification["requirement"] = "Skill development"

        else:
            job_phrases = [
                "job",
                "placement",
                "employment",
                "career opportunity",
                "career opportunities",
                "career growth",
                "build my career",
                "start my career",
                "career goal",
            ]

            if any(phrase in message_lower for phrase in job_phrases):
                qualification["requirement"] = "Job"

    return qualification


# =========================================================
# MERGE QUALIFICATION MEMORY
# =========================================================

def merge_qualification(
    old_qualification: dict,
    new_qualification: dict,
) -> dict:
    """
    Preserve existing qualification data.
    Combine new interests without duplicates.
    Update other fields only when a new value exists.
    """

    old_qualification = old_qualification or {}
    new_qualification = new_qualification or {}

    merged = old_qualification.copy()

    old_interest = old_qualification.get("interest")
    new_interest = new_qualification.get("interest")

    if new_interest:
        old_items = [
            item.strip()
            for item in str(old_interest or "").split(",")
            if item.strip()
        ]

        new_items = [
            item.strip()
            for item in str(new_interest).split(",")
            if item.strip()
        ]

        combined = old_items.copy()
        existing = {item.casefold() for item in combined}

        for item in new_items:
            if item.casefold() not in existing:
                combined.append(item)
                existing.add(item.casefold())

        merged["interest"] = ", ".join(combined)

    for key in ["budget", "timeline", "requirement"]:
        value = new_qualification.get(key)

        if value is None:
            continue

        if isinstance(value, str):
            value = value.strip()

            if not value:
                continue

        merged[key] = value

    return merged
