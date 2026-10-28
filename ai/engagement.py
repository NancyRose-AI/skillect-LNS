from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List


# =========================================================
# TIMEZONE
# =========================================================

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


# =========================================================
# CONTENT TYPES
# =========================================================

CONTENT_TYPES = [
    "educational",
    "career_tip",
    "industry_update",
    "newsletter",
    "image",
    "batch_update",
]


# =========================================================
# OPT-OUT DETECTION
# =========================================================

OPT_OUT_PHRASES = [
    "not interested",
    "i am not interested",
    "i'm not interested",
    "dont message",
    "don't message",
    "do not message",
    "stop messaging",
    "stop message",
    "stop sending",
    "unsubscribe",
    "remove me",
    "leave me",
    "no more messages",
]


def is_opted_out(message: Optional[str]) -> bool:
    """
    Detect whether the lead explicitly asked us to stop messaging.
    """

    if not message:
        return False

    text = message.lower().strip()

    return any(
        phrase in text
        for phrase in OPT_OUT_PHRASES
    )


# =========================================================
# INTEREST NORMALIZATION
# =========================================================

def normalize_interest(
    interest: Optional[str],
) -> str:

    if not interest:
        return "cloud"

    value = interest.lower().strip()

    if "aws" in value:
        return "aws"

    if "azure" in value:
        return "azure"

    if "devops" in value:
        return "devops"

    if "python" in value:
        return "python"

    if "cloud" in value:
        return "cloud"

    return "cloud"


# =========================================================
# CONTENT TOPIC
# =========================================================

def get_content_topic(
    interest: Optional[str],
) -> str:

    normalized = normalize_interest(
        interest
    )

    topics = {
        "aws": "AWS Cloud Engineering",
        "azure": "Azure Cloud Engineering",
        "devops": "DevOps",
        "python": "Python",
        "cloud": "Cloud Engineering",
    }

    return topics.get(
        normalized,
        "Cloud Engineering",
    )


# =========================================================
# ENGAGEMENT FREQUENCY
# =========================================================

def get_minimum_gap_days(
    ai_temperature: str,
) -> int:
    """
    Minimum gap before another automatic engagement.

    COLD:
        Light nurturing.
        Don't contact too frequently.

    WARM:
        More active nurturing because
        the lead has shown stronger interest.

    HOT:
        Automatic nurturing stops.
        HOT leads go to sales workflow.
    """

    temperature = (
        ai_temperature or "cold"
    ).lower()

    if temperature == "warm":
        return 5

    if temperature == "cold":
        return 10

    return 0


def get_monthly_limit(
    ai_temperature: str,
) -> int:
    """
    Safety limit.

    This is NOT a target.

    COLD:
        Maximum 3 automatic messages
        during the 30-day period.

    WARM:
        Maximum 4 automatic messages
        during the 30-day period.

    HOT:
        No automatic nurturing.
    """

    temperature = (
        ai_temperature or "cold"
    ).lower()

    if temperature == "cold":
        return 3

    if temperature == "warm":
        return 4

    return 0


# =========================================================
# CONTENT SELECTION
# =========================================================

def choose_content_type(
    ai_temperature: str,
    previous_content_types: Optional[
        List[str]
    ] = None,
    batch_available: bool = False,
) -> Optional[str]:
    """
    Select content based on lead temperature.

    COLD:
        Light nurturing only.

        - educational
        - career_tip

    WARM:
        Active nurturing.

        - educational
        - career_tip
        - industry_update
        - image
        - newsletter
        - real batch_update

    HOT:
        No nurturing content.
    """

    previous_content_types = (
        previous_content_types or []
    )

    temperature = (
        ai_temperature or "cold"
    ).lower()

    # Look only at recent content types
    # to avoid repeating the same type.
    recent = previous_content_types[-3:]

    # =====================================================
    # COLD LEAD
    # =====================================================

    if temperature == "cold":

        cold_rotation = [
            "educational",
            "career_tip",
        ]

        for content_type in cold_rotation:

            if content_type not in recent:
                return content_type

        # Both appeared recently.
        # Restart with educational content.
        return "educational"

    # =====================================================
    # WARM LEAD
    # =====================================================

    if temperature == "warm":

        # A batch update can only be selected
        # when a REAL batch is available.
        if (
            batch_available
            and "batch_update" not in recent
        ):
            return "batch_update"

        warm_rotation = [
            "educational",
            "career_tip",
            "industry_update",
            "image",
            "newsletter",
        ]

        for content_type in warm_rotation:

            if content_type not in recent:
                return content_type

        # If all available content types
        # were recently used, restart.
        return "educational"

    # =====================================================
    # HOT / UNKNOWN
    # =====================================================

    return None


# =========================================================
# MAIN ENGAGEMENT DECISION
# =========================================================

def decide_engagement(
    *,
    ai_temperature: str,
    interest: Optional[str] = None,
    lead_status: Optional[str] = None,
    last_lead_message: Optional[str] = None,
    last_sent_at: Optional[datetime] = None,
    messages_sent_last_30_days: int = 0,
    previous_content_types: Optional[
        List[str]
    ] = None,
    lead_replied_recently: bool = False,
    batch_available: bool = False,
    current_time: Optional[datetime] = None,
) -> dict:

    """
    Decide whether the lead should receive
    an automatic engagement message.

    IMPORTANT:

    This function does NOT send WhatsApp
    messages.

    It only decides:

        - eligible or not
        - reason
        - content type
        - topic
    """

    if current_time is None:
        current_time = datetime.now(
            INDIA_TIMEZONE
        )

    temperature = (
        ai_temperature or "cold"
    ).lower()

    status = (
        lead_status or "new"
    ).lower()

    previous_content_types = (
        previous_content_types or []
    )

    # =====================================================
    # 1. CLOSED LEADS
    # =====================================================

    if status in [
        "converted",
        "lost",
        "closed",
    ]:

        return {
            "eligible": False,
            "reason": "lead_closed",
            "content_type": None,
            "topic": None,
        }

    # =====================================================
    # 2. EXPLICIT OPT-OUT
    # =====================================================

    if is_opted_out(
        last_lead_message
    ):

        return {
            "eligible": False,
            "reason": "lead_opted_out",
            "content_type": None,
            "topic": None,
        }

    # =====================================================
    # 3. HOT LEAD
    # =====================================================

    if temperature == "hot":

        return {
            "eligible": False,
            "reason": "hot_lead_send_to_sales",
            "content_type": None,
            "topic": None,
        }

    # =====================================================
    # 4. RECENT LEAD REPLY
    # =====================================================

    if lead_replied_recently:

        return {
            "eligible": False,
            "reason": (
                "lead_replied_wait_for_ai_conversation"
            ),
            "content_type": None,
            "topic": None,
        }

    # =====================================================
    # 5. MONTHLY SAFETY LIMIT
    # =====================================================

    monthly_limit = get_monthly_limit(
        temperature
    )

    if (
        messages_sent_last_30_days
        >= monthly_limit
    ):

        return {
            "eligible": False,
            "reason": (
                "monthly_safety_limit_reached"
            ),
            "content_type": None,
            "topic": None,
        }

    # =====================================================
    # 6. FREQUENCY / GAP CHECK
    # =====================================================

    minimum_gap_days = (
        get_minimum_gap_days(
            temperature
        )
    )

    if last_sent_at:

        # Make timezone aware if the DB
        # returned a naive datetime.
        if last_sent_at.tzinfo is None:

            last_sent_at = (
                last_sent_at.replace(
                    tzinfo=INDIA_TIMEZONE
                )
            )

        next_allowed_time = (
            last_sent_at
            + timedelta(
                days=minimum_gap_days
            )
        )

        if (
            current_time
            < next_allowed_time
        ):

            return {
                "eligible": False,
                "reason": (
                    "waiting_for_next_engagement_window"
                ),
                "content_type": None,
                "topic": get_content_topic(
                    interest
                ),
                "next_allowed_at": (
                    next_allowed_time.isoformat()
                ),
            }

    # =====================================================
    # 7. SELECT CONTENT
    # =====================================================

    content_type = choose_content_type(
        ai_temperature=temperature,
        previous_content_types=(
            previous_content_types
        ),
        batch_available=batch_available,
    )

    topic = get_content_topic(
        interest
    )

    # =====================================================
    # 8. FINAL DECISION
    # =====================================================

    return {
        "eligible": True,
        "reason": "engagement_allowed",
        "content_type": content_type,
        "topic": topic,
        "ai_temperature": temperature,
        "messages_sent_last_30_days": (
            messages_sent_last_30_days
        ),
        "monthly_safety_limit": (
            monthly_limit
        ),
        "minimum_gap_days": (
            minimum_gap_days
        ),
    }