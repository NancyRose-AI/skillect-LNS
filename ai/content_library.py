from typing import Optional, Dict, Any


# =========================================================
# APPROVED EDUCATIONAL CONTENT
# =========================================================

EDUCATIONAL_CONTENT = {

    "AWS Cloud Engineering": (
        "AWS Cloud Engineering focuses on practical cloud skills. "
        "Skillect's approved AWS course topics include Amazon EC2, "
        "Amazon S3, IAM, VPC, EFS, RDS, Elastic Load Balancer, "
        "and CloudWatch."
    ),

    "Azure Cloud Engineering": (
        "Azure Cloud Engineering focuses on practical Microsoft Azure "
        "cloud services. Skillect's approved Azure course topics include "
        "Azure Virtual Machines, Blob Storage, Microsoft Entra ID, "
        "VNet, Azure SQL Database, Azure Load Balancer, and Azure Monitor."
    ),
}


# =========================================================
# APPROVED CAREER CONTENT
# =========================================================

CAREER_CONTENT = {

    "AWS Cloud Engineering": (
        "If you're building a career in cloud engineering, practical "
        "experience is important along with understanding AWS concepts. "
        "Skillect's AWS Cloud Engineering training includes practical "
        "cloud learning, interview preparation, and cloud project guidance."
    ),

    # We intentionally do not copy AWS-specific career-support claims
    # to Azure because those details are not currently approved.
    "Azure Cloud Engineering": (
        "If you're interested in Azure Cloud Engineering, Skillect offers "
        "a 3-month Azure Cloud Engineering course covering practical Azure "
        "services. Basic computer knowledge is enough to begin the training."
    ),
}


# =========================================================
# VERIFIED CONTENT TYPES
# =========================================================

VERIFIED_CONTENT_TYPES = {
    "industry_update",
    "newsletter",
    "image",
    "batch_update",
}


# =========================================================
# GET EDUCATIONAL CONTENT
# =========================================================

def get_educational_content(
    topic: Optional[str],
) -> Optional[str]:

    if not topic:
        return None

    return EDUCATIONAL_CONTENT.get(topic)


# =========================================================
# GET CAREER CONTENT
# =========================================================

def get_career_content(
    topic: Optional[str],
) -> Optional[str]:

    if not topic:
        return None

    return CAREER_CONTENT.get(topic)


# =========================================================
# GET CONTENT
# =========================================================

def get_content(
    content_type: Optional[str],
    topic: Optional[str],
) -> Dict[str, Any]:

    if not content_type:

        return {
            "ready": False,
            "reason": "content_type_missing",
            "content_type": None,
            "topic": topic,
            "message": None,
        }

    content_type = content_type.lower().strip()

    # -----------------------------------------------------
    # EDUCATIONAL
    # -----------------------------------------------------

    if content_type == "educational":

        message = get_educational_content(topic)

        if not message:

            return {
                "ready": False,
                "reason": "approved_content_not_found",
                "content_type": content_type,
                "topic": topic,
                "message": None,
            }

        return {
            "ready": True,
            "reason": "approved_content_found",
            "content_type": content_type,
            "topic": topic,
            "message": message,
        }

    # -----------------------------------------------------
    # CAREER TIP
    # -----------------------------------------------------

    if content_type == "career_tip":

        message = get_career_content(topic)

        if not message:

            return {
                "ready": False,
                "reason": "approved_content_not_found",
                "content_type": content_type,
                "topic": topic,
                "message": None,
            }

        return {
            "ready": True,
            "reason": "approved_content_found",
            "content_type": content_type,
            "topic": topic,
            "message": message,
        }

    # -----------------------------------------------------
    # VERIFIED / EXTERNAL CONTENT
    #
    # Do NOT invent these using the LLM.
    # Later these will come from:
    #
    # industry_update -> trusted verified source
    # newsletter      -> approved content
    # image           -> approved image/infographic
    # batch_update    -> real batch data
    # -----------------------------------------------------

    if content_type in VERIFIED_CONTENT_TYPES:

        return {
            "ready": False,
            "reason": "verified_content_required",
            "content_type": content_type,
            "topic": topic,
            "message": None,
        }

    # -----------------------------------------------------
    # UNKNOWN CONTENT TYPE
    # -----------------------------------------------------

    return {
        "ready": False,
        "reason": "unsupported_content_type",
        "content_type": content_type,
        "topic": topic,
        "message": None,
    }
# =========================================================
# PERSONALIZE APPROVED NURTURE CONTENT
# =========================================================

def personalize_content(
    message: str,
    lead_name: Optional[str] = None,
    interest: Optional[str] = None,
    budget: Optional[Any] = None,
    timeline: Optional[str] = None,
    requirement: Optional[str] = None,
) -> str:
    """Personalize approved content using saved lead details."""

    parts = []

    if lead_name and lead_name.strip():
        parts.append(f"Hi {lead_name.strip()},")

    parts.append(message.strip())

    if interest and interest.strip():
        parts.append(f"Your area of interest is {interest.strip()}.")

    if timeline and timeline.strip():
        parts.append(f"Your planned timeline is {timeline.strip()}.")

    if requirement and requirement.strip():
        parts.append(f"Your current goal is {requirement.strip()}.")

    if budget is not None:
        parts.append(f"Your indicated budget is {budget}.")

    parts.append(
        "Please let our team know if you would like more details."
    )

    return "\n\n".join(parts)