
from datetime import datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models import Lead, Conversation, NurtureMessage

from ai.nurturing import is_not_interested
from ai.engagement import decide_engagement
from ai.content_library import (
    get_content,
    personalize_content,
)


# =========================================================
# CONFIGURATION
# =========================================================

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


# =========================================================
# CURRENT TIME
# =========================================================

def get_current_time() -> datetime:
    return datetime.now(INDIA_TIMEZONE)


# =========================================================
# MAKE DATETIME TIMEZONE-AWARE
# =========================================================

def ensure_timezone(
    value: Optional[datetime],
) -> Optional[datetime]:

    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=INDIA_TIMEZONE)

    return value


# =========================================================
# GET LATEST LEAD MESSAGE
# =========================================================

def get_latest_lead_message(
    db: Session,
    lead_id: int,
) -> Optional[Conversation]:

    return (
        db.query(Conversation)
        .filter(
            Conversation.lead_id == lead_id,
            Conversation.role == "lead",
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )


# =========================================================
# GET LAST SENT NURTURE MESSAGE
# =========================================================

def get_last_sent_nurture(
    db: Session,
    lead_id: int,
) -> Optional[NurtureMessage]:

    return (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.lead_id == lead_id,
            NurtureMessage.status == "sent",
            NurtureMessage.sent_at.isnot(None),
        )
        .order_by(NurtureMessage.sent_at.desc())
        .first()
    )


# =========================================================
# COUNT MESSAGES SENT DURING LAST 30 DAYS
# =========================================================

def get_last_30_days_sent_count(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
) -> int:

    if current_time is None:
        current_time = get_current_time()

    current_time = ensure_timezone(current_time)

    period_start = current_time - timedelta(days=30)

    return (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.lead_id == lead_id,
            NurtureMessage.status == "sent",
            NurtureMessage.sent_at.isnot(None),
            NurtureMessage.sent_at >= period_start,
            NurtureMessage.sent_at <= current_time,
        )
        .count()
    )


# =========================================================
# GET PREVIOUS CONTENT TYPES
# =========================================================

def get_previous_content_types(
    db: Session,
    lead_id: int,
    limit: int = 5,
) -> List[str]:

    records = (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.lead_id == lead_id,
            NurtureMessage.content_type.isnot(None),
            NurtureMessage.status.in_(["generated", "sent"]),
        )
        .order_by(NurtureMessage.created_at.desc())
        .limit(limit)
        .all()
    )

    # Reverse newest-to-oldest records so the
    # engagement engine receives oldest-to-newest.

    return [
        record.content_type
        for record in reversed(records)
        if record.content_type
    ]


# =========================================================
# SAME-DAY DUPLICATE CHECK
# =========================================================

def has_nurture_today(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
) -> bool:

    if current_time is None:
        current_time = get_current_time()

    current_time = ensure_timezone(current_time)

    day_start = current_time.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    day_end = day_start + timedelta(days=1)

    existing = (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.lead_id == lead_id,
            NurtureMessage.created_at >= day_start,
            NurtureMessage.created_at < day_end,
            NurtureMessage.status.in_(["generated", "sent"]),
        )
        .first()
    )

    return existing is not None


# =========================================================
# CHECK WHETHER LEAD REPLIED AFTER LAST NURTURE
# =========================================================

def lead_replied_after_nurture(
    db: Session,
    lead_id: int,
) -> bool:

    last_nurture = get_last_sent_nurture(db, lead_id)

    if not last_nurture:
        return False

    latest_lead_message = get_latest_lead_message(
        db,
        lead_id,
    )

    if not latest_lead_message:
        return False

    lead_message_time = ensure_timezone(
        latest_lead_message.created_at
    )

    nurture_time = ensure_timezone(
        last_nurture.sent_at
    )

    if not lead_message_time or not nurture_time:
        return False

    return lead_message_time > nurture_time


# =========================================================
# GET ENGAGEMENT HISTORY
# =========================================================

def get_engagement_history(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
) -> dict:

    if current_time is None:
        current_time = get_current_time()

    last_sent = get_last_sent_nurture(db, lead_id)

    previous_content_types = get_previous_content_types(
        db,
        lead_id,
    )

    sent_last_30_days = get_last_30_days_sent_count(
        db,
        lead_id,
        current_time,
    )

    replied_recently = lead_replied_after_nurture(
        db,
        lead_id,
    )

    return {
        "last_sent_at": (
            last_sent.sent_at if last_sent else None
        ),
        "messages_sent_last_30_days": sent_last_30_days,
        "previous_content_types": previous_content_types,
        "lead_replied_recently": replied_recently,
    }


# =========================================================
# PREPARE NURTURE FOR LEAD
# =========================================================

def prepare_nurture_for_lead(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
    batch_available: bool = False,
):

    if current_time is None:
        current_time = get_current_time()

    current_time = ensure_timezone(current_time)

    # -----------------------------------------------------
    # 1. FIND LEAD
    # -----------------------------------------------------

    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id)
        .first()
    )

    if not lead:
        return {
            "eligible": False,
            "reason": "lead_not_found",
        }

    # -----------------------------------------------------
    # 2. CHECK LEAD STATUS
    # -----------------------------------------------------

    status = (lead.status or "new").lower().strip()

    if status in {"converted", "lost", "closed"}:
        return {
            "eligible": False,
            "reason": "lead_closed",
        }

    # -----------------------------------------------------
    # 3. GET LATEST LEAD MESSAGE
    # -----------------------------------------------------

    latest_conversation = get_latest_lead_message(
        db,
        lead_id,
    )

    latest_message = (
        latest_conversation.message
        if latest_conversation
        else None
    )

    # -----------------------------------------------------
    # 4. EXPLICIT OPT-OUT
    # -----------------------------------------------------

    if is_not_interested(latest_message):
        return {
            "eligible": False,
            "reason": "lead_opted_out",
        }

    # -----------------------------------------------------
    # 5. GET ENGAGEMENT HISTORY
    # -----------------------------------------------------

    history = get_engagement_history(
        db,
        lead_id,
        current_time,
    )

    # -----------------------------------------------------
    # 6. SAME-DAY DUPLICATE PROTECTION
    # -----------------------------------------------------

    if has_nurture_today(
        db,
        lead_id,
        current_time,
    ):
        return {
            "eligible": False,
            "reason": "already_generated_today",
        }

    # -----------------------------------------------------
    # 7. ASK ENGAGEMENT ENGINE
    # -----------------------------------------------------

    decision = decide_engagement(
        ai_temperature=lead.ai_temperature,
        interest=lead.interest,
        lead_status=lead.status,
        last_lead_message=latest_message,
        last_sent_at=history["last_sent_at"],
        messages_sent_last_30_days=history[
            "messages_sent_last_30_days"
        ],
        previous_content_types=history[
            "previous_content_types"
        ],
        lead_replied_recently=history[
            "lead_replied_recently"
        ],
        batch_available=batch_available,
        current_time=current_time,
    )

    # -----------------------------------------------------
    # 8. ENGAGEMENT NOT ALLOWED
    # -----------------------------------------------------

    if not decision.get("eligible"):
        return {
            **decision,
            "lead_id": lead.id,
        }

    content_type = decision.get("content_type")
    topic = decision.get("topic")

    # -----------------------------------------------------
    # 9. GET APPROVED CONTENT
    # -----------------------------------------------------

    content_result = get_content(
        content_type,
        topic,
    )

    # -----------------------------------------------------
    # 10. CONTENT NOT READY
    # -----------------------------------------------------

    if not content_result.get("ready"):
        return {
            "eligible": True,
            "ready_to_send": False,
            "reason": content_result.get("reason"),
            "lead_id": lead.id,
            "content_type": content_type,
            "topic": topic,
            "messages_sent_last_30_days": history[
                "messages_sent_last_30_days"
            ],
            "previous_content_types": history[
                "previous_content_types"
            ],
        }

    # -----------------------------------------------------
    # 11. GET APPROVED MESSAGE
    # -----------------------------------------------------

    message = content_result.get("message")

    if not message:
        return {
            "eligible": True,
            "ready_to_send": False,
            "reason": "content_message_missing",
            "lead_id": lead.id,
            "content_type": content_type,
            "topic": topic,
        }

    # -----------------------------------------------------
    # 12. PERSONALIZE APPROVED CONTENT
    #
    # Uses existing database values.
    # Does not generate new course claims.
    # -----------------------------------------------------

    message = personalize_content(
        message=message,
        lead_name=lead.name,
        interest=lead.interest,
        budget=lead.budget,
        timeline=lead.timeline,
        requirement=lead.requirement,
    )

    # -----------------------------------------------------
    # 13. DETERMINE ENGAGEMENT STAGE
    # -----------------------------------------------------

    total_previous_records = (
        db.query(NurtureMessage)
        .filter(NurtureMessage.lead_id == lead_id)
        .count()
    )

    stage = total_previous_records + 1

    # -----------------------------------------------------
    # 14. SAVE GENERATED MESSAGE
    #
    # Generated does not mean sent.
    # No WhatsApp message is sent here.
    # -----------------------------------------------------

    nurture_record = NurtureMessage(
        lead_id=lead.id,
        message=message,
        content_type=content_type,
        topic=topic,
        stage=stage,
        status="generated",
    )

    try:
        db.add(nurture_record)
        db.commit()
        db.refresh(nurture_record)

    except Exception:
        db.rollback()
        raise

    # -----------------------------------------------------
    # 15. RETURN GENERATED MESSAGE
    # -----------------------------------------------------

    return {
        "eligible": True,
        "ready_to_send": True,
        "reason": "engagement_generated",
        "nurture_id": nurture_record.id,
        "lead_id": lead.id,
        "stage": stage,
        "content_type": nurture_record.content_type,
        "topic": nurture_record.topic,
        "messages_sent_last_30_days": history[
            "messages_sent_last_30_days"
        ],
        "previous_content_types": history[
            "previous_content_types"
        ],
        "message": nurture_record.message,
    }


# =========================================================
# MARK MESSAGE AS SENT
# =========================================================

def mark_nurture_sent(
    db: Session,
    nurture_id: int,
    sent_time: Optional[datetime] = None,
):

    if sent_time is None:
        sent_time = get_current_time()

    sent_time = ensure_timezone(sent_time)

    record = (
        db.query(NurtureMessage)
        .filter(NurtureMessage.id == nurture_id)
        .first()
    )

    if not record:
        return {
            "success": False,
            "reason": "nurture_message_not_found",
        }

    # -----------------------------------------------------
    # PREVENT DOUBLE SENT UPDATE
    # -----------------------------------------------------

    if record.status == "sent":
        return {
            "success": False,
            "reason": "already_sent",
        }

    # -----------------------------------------------------
    # MARK AS SENT
    # -----------------------------------------------------

    record.status = "sent"
    record.sent_at = sent_time

    try:
        db.commit()
        db.refresh(record)

    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "nurture_id": record.id,
        "lead_id": record.lead_id,
        "stage": record.stage,
        "content_type": record.content_type,
        "topic": record.topic,
        "sent_at": record.sent_at,
    }
