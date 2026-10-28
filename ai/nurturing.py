from typing import Optional


# =========================================================
# NOT INTERESTED / OPT-OUT PHRASES
# =========================================================

NOT_INTERESTED_PHRASES = {
    "not interested",
    "i am not interested",
    "i'm not interested",
    "im not interested",

    "no thanks",
    "no thank you",

    "stop",
    "stop messaging",
    "stop messaging me",
    "stop sending messages",

    "don't message me",
    "dont message me",
    "do not message me",

    "don't contact me",
    "dont contact me",
    "do not contact me",

    "unsubscribe",
    "remove me",
    "leave me alone",
}


# =========================================================
# NORMALIZE MESSAGE
# =========================================================

def normalize_message(
    message: Optional[str],
) -> str:

    if not message:
        return ""

    return " ".join(
        message.lower().strip().split()
    )


# =========================================================
# CHECK IF LEAD OPTED OUT
# =========================================================

def is_not_interested(
    message: Optional[str],
) -> bool:

    text = normalize_message(message)

    if not text:
        return False

    # Exact match
    if text in NOT_INTERESTED_PHRASES:
        return True

    # Detect phrase inside a longer message
    for phrase in NOT_INTERESTED_PHRASES:

        if phrase in text:
            return True

    return False