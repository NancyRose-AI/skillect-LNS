from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


# =========================================================
# CONFIGURATION
# =========================================================

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Monday = 0
# Wednesday = 2
# Saturday = 5
NURTURE_DAYS = {0, 2, 5}

# Maximum nurturing messages per lead per week
WEEKLY_SEND_LIMIT = 3


# =========================================================
# STOP / OPT-OUT DETECTION
# =========================================================

STOP_PHRASES = [
    "not interested",
    "i am not interested",
    "i'm not interested",
    "dont contact me",
    "don't contact me",
    "do not contact me",
    "stop messaging",
    "stop sending messages",
    "do not message me",
    "don't message me",
    "unsubscribe",
    "no thanks",
    "no thank you",
]


def is_not_interested(
    message: Optional[str],
) -> bool:
    """
    Detect whether the lead explicitly asked us
    to stop contacting them.
    """

    if not message:
        return False

    text = message.lower().strip()

    return any(
        phrase in text
        for phrase in STOP_PHRASES
    )


# =========================================================
# INTEREST NORMALIZATION
# =========================================================

def normalize_interest(
    interest: Optional[str],
) -> str:

    if not interest:
        return "general"

    text = interest.lower().strip()

    if "aws" in text:
        return "aws"

    if "azure" in text:
        return "azure"

    if (
        "artificial intelligence" in text
        or text == "ai"
        or " ai " in f" {text} "
    ):
        return "ai"

    if "cloud" in text:
        return "cloud"

    return "general"


# =========================================================
# WEEKLY SCHEDULE
# =========================================================

def is_nurture_day(
    current_time: Optional[datetime] = None,
) -> bool:
    """
    Returns True only on:
    Monday
    Wednesday
    Saturday
    """

    if current_time is None:
        current_time = datetime.now(
            INDIA_TIMEZONE
        )

    return current_time.weekday() in NURTURE_DAYS


# =========================================================
# CHECK WHETHER MESSAGE CAN BE SENT
# =========================================================

def can_send_nurture(
    ai_temperature: Optional[str],
    messages_sent_this_week: int,
    last_message: Optional[str] = None,
    lead_replied: bool = False,
    current_time: Optional[datetime] = None,
) -> bool:
    """
    Safety rules for automated cold-lead nurturing.
    """

    # ---------------------------------------------
    # Explicit opt-out
    # ---------------------------------------------

    if is_not_interested(last_message):
        return False

    # ---------------------------------------------
    # If lead replied, pause automatic nurturing
    # ---------------------------------------------

    if lead_replied:
        return False

    # ---------------------------------------------
    # Only COLD leads
    # ---------------------------------------------

    temperature = (
        ai_temperature or ""
    ).lower().strip()

    if temperature != "cold":
        return False

    # ---------------------------------------------
    # Maximum 3 messages per week
    # ---------------------------------------------

    if messages_sent_this_week >= WEEKLY_SEND_LIMIT:
        return False

    # ---------------------------------------------
    # Only scheduled days
    # ---------------------------------------------

    if not is_nurture_day(current_time):
        return False

    return True


# =========================================================
# NURTURING MESSAGE TEMPLATES
# =========================================================

NURTURE_MESSAGES = {

    # =====================================================
    # AWS
    # =====================================================

    "aws": {
        1: (
            "Hi! Since you're interested in AWS, "
            "Skillect's AWS Cloud Engineering course "
            "covers Amazon EC2, Amazon S3, IAM, VPC, "
            "EFS, RDS, Elastic Load Balancer, and "
            "CloudWatch. Would you like to know more "
            "about the course?"
        ),

        2: (
            "If you're planning to build your AWS skills, "
            "the Skillect AWS Cloud Engineering course "
            "runs for 3 months and focuses on practical "
            "cloud engineering learning. Would you like "
            "to know how to get started?"
        ),

        3: (
            "AWS Cloud Engineering training at Skillect "
            "is suitable for fresh graduates, beginners, "
            "students looking for cloud jobs, and career "
            "switchers. If you're still interested, "
            "I can share the course details."
        ),
    },

    # =====================================================
    # AZURE
    # =====================================================

    "azure": {
        1: (
            "Hi! Since you're interested in Azure, "
            "Skillect's Azure Cloud Engineering course "
            "covers Azure Virtual Machines, Azure Blob "
            "Storage, Microsoft Entra ID, Azure Virtual "
            "Network, Azure SQL Database, Azure Load "
            "Balancer, and Azure Monitor. Would you "
            "like to know more?"
        ),

        2: (
            "If you're planning to learn Azure, "
            "Skillect's Azure Cloud Engineering course "
            "runs for 3 months and the course fee is "
            "₹25,000. Would you like more details?"
        ),

        3: (
            "Basic computer knowledge is enough to start "
            "the Azure Cloud Engineering course. "
            "If you're still interested, I can help you "
            "explore the course details."
        ),
    },

    # =====================================================
    # AI
    # =====================================================

    "ai": {
        1: (
            "Hi! I noticed you're exploring AI-related "
            "learning. Skillect currently has Cloud "
            "Engineering training options in AWS and "
            "Azure. If cloud learning is relevant to "
            "your goal, I can share the available options."
        ),

        2: (
            "If you're also considering cloud skills, "
            "I can help you compare the AWS and Azure "
            "Cloud Engineering courses currently "
            "available at Skillect."
        ),

        3: (
            "If you'd like to explore cloud engineering "
            "alongside your AI interest, I can help you "
            "choose between the available AWS and Azure "
            "training options."
        ),
    },

    # =====================================================
    # CLOUD
    # =====================================================

    "cloud": {
        1: (
            "Hi! Since you're interested in Cloud "
            "Computing, Skillect currently offers AWS "
            "Cloud Engineering and Azure Cloud "
            "Engineering courses. Which one would you "
            "like to explore?"
        ),

        2: (
            "Both AWS and Azure Cloud Engineering "
            "courses are available at Skillect. "
            "If you'd like, I can share their available "
            "course details to help you choose."
        ),

        3: (
            "If your goal is to learn cloud engineering, "
            "I can help you explore the AWS and Azure "
            "training options available at Skillect."
        ),
    },

    # =====================================================
    # GENERAL / UNKNOWN INTEREST
    # =====================================================

    "general": {
        1: (
            "Hi! Skillect currently offers Cloud "
            "Engineering training in AWS and Azure. "
            "If you're exploring cloud learning, "
            "I can help you find a relevant option."
        ),

        2: (
            "If you're interested in learning Cloud "
            "Engineering, I can share information about "
            "the AWS and Azure courses available at "
            "Skillect."
        ),

        3: (
            "Just checking in. If you'd like to explore "
            "AWS or Azure Cloud Engineering training, "
            "I can share the available course details."
        ),
    },
}


# =========================================================
# GENERATE NURTURING MESSAGE
# =========================================================

def generate_nurture_message(
    interest: Optional[str],
    ai_temperature: Optional[str],
    messages_sent_this_week: int = 0,
    last_message: Optional[str] = None,
    lead_replied: bool = False,
    current_time: Optional[datetime] = None,
) -> Optional[str]:
    """
    Generate one nurturing message.

    Rules:
    - COLD leads only
    - Maximum 3 messages per week
    - Monday / Wednesday / Saturday only
    - Stop if lead opts out
    - Pause if lead replies
    """

    allowed = can_send_nurture(
        ai_temperature=ai_temperature,
        messages_sent_this_week=messages_sent_this_week,
        last_message=last_message,
        lead_replied=lead_replied,
        current_time=current_time,
    )

    if not allowed:
        return None

    # ---------------------------------------------
    # Message number:
    #
    # 0 already sent -> Message 1
    # 1 already sent -> Message 2
    # 2 already sent -> Message 3
    # ---------------------------------------------

    stage = messages_sent_this_week + 1

    topic = normalize_interest(
        interest
    )

    topic_messages = NURTURE_MESSAGES.get(
        topic,
        NURTURE_MESSAGES["general"],
    )

    return topic_messages.get(stage)