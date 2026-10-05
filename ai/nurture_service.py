from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models import Lead, Conversation, NurtureMessage
from ai.nurturing import (
    generate_nurture_message,
    is_not_interested,
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
# CURRENT WEEK RANGE
# =========================================================

def get_week_range(
    current_time: Optional[datetime] = None,
):
    """
    Returns:
    Monday 00:00
    to
    Next Monday 00:00
    """

    if current_time is None:
        current_time = get_current_time()

    if current_time.tzinfo is None:
        current_time = current_time.replace(
            tzinfo=INDIA_TIMEZONE
        )

    week_start = (
        current_time
        - timedelta(days=current_time.weekday())
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    week_end = week_start + timedelta(days=7)

    return week_start, week_end


# =========================================================
# WEEKLY SENT COUNT
# =========================================================

def get_weekly_sent_count(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
) -> int:

    week_start, week_end = get_week_range(
        current_time
    )

    return (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.lead_id == lead_id,
            NurtureMessage.status == "sent",
            NurtureMessage.sent_at >= week_start,
            NurtureMessage.sent_at < week_end,
        )
        .count()
    )


# =========================================================
# SAME DAY DUPLICATE CHECK
# =========================================================

def has_nurture_today(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
) -> bool:

    if current_time is None:
        current_time = get_current_time()

    if current_time.tzinfo is None:
        current_time = current_time.replace(
            tzinfo=INDIA_TIMEZONE
        )

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
            NurtureMessage.status.in_(
                ["generated", "sent"]
            ),
        )
        .first()
    )

    return existing is not None


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
        .order_by(
            Conversation.created_at.desc()
        )
        .first()
    )


# =========================================================
# CHECK WHETHER LEAD REPLIED AFTER LAST NURTURE
# =========================================================

def lead_replied_after_nurture(
    db: Session,
    lead_id: int,
) -> bool:

    last_nurture = (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.lead_id == lead_id,
            NurtureMessage.status == "sent",
            NurtureMessage.sent_at.isnot(None),
        )
        .order_by(
            NurtureMessage.sent_at.desc()
        )
        .first()
    )

    # No previous nurture message
    if not last_nurture:
        return False

    latest_lead_message = get_latest_lead_message(
        db,
        lead_id,
    )

    if not latest_lead_message:
        return False

    return (
        latest_lead_message.created_at
        > last_nurture.sent_at
    )


# =========================================================
# PREPARE NURTURING MESSAGE
# =========================================================

def prepare_nurture_for_lead(
    db: Session,
    lead_id: int,
    current_time: Optional[datetime] = None,
):

    if current_time is None:
        current_time = get_current_time()

    # -----------------------------------------------------
    # Find lead
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
    # Do not nurture closed leads
    # -----------------------------------------------------

    status = (
        lead.status or ""
    ).lower().strip()

    if status in {
        "converted",
        "lost",
        "closed",
    }:
        return {
            "eligible": False,
            "reason": "lead_closed",
        }

    # -----------------------------------------------------
    # Latest lead message
    # -----------------------------------------------------

    latest_conversation = get_latest_lead_message(
        db,
        lead_id,
    )

    latest_message = None

    if latest_conversation:
        latest_message = latest_conversation.message

    # -----------------------------------------------------
    # Explicit NOT INTERESTED / STOP
    # -----------------------------------------------------

    if is_not_interested(latest_message):
        return {
            "eligible": False,
            "reason": "lead_opted_out",
        }

    # -----------------------------------------------------
    # Only AI COLD leads
    # -----------------------------------------------------

    ai_temperature = (
        lead.ai_temperature or ""
    ).lower().strip()

    if ai_temperature != "cold":
        return {
            "eligible": False,
            "reason": "not_cold_lead",
            "ai_temperature": ai_temperature,
        }

    # -----------------------------------------------------
    # If lead replied after last nurture, pause
    # -----------------------------------------------------

    if lead_replied_after_nurture(
        db,
        lead_id,
    ):
        return {
            "eligible": False,
            "reason": "lead_replied",
        }

    # -----------------------------------------------------
    # Prevent duplicate same-day message
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
    # Count THIS WEEK sent messages
    # -----------------------------------------------------

    weekly_count = get_weekly_sent_count(
        db,
        lead_id,
        current_time,
    )

    if weekly_count >= 3:
        return {
            "eligible": False,
            "reason": "weekly_limit_reached",
            "messages_sent_this_week": weekly_count,
        }

    # -----------------------------------------------------
    # Generate relevant message
    # -----------------------------------------------------

    message = generate_nurture_message(
        interest=lead.interest,
        ai_temperature=lead.ai_temperature,
        messages_sent_this_week=weekly_count,
        last_message=latest_message,
        lead_replied=False,
        current_time=current_time,
    )

    if message is None:
        return {
            "eligible": False,
            "reason": "not_scheduled_today",
            "messages_sent_this_week": weekly_count,
        }

    # -----------------------------------------------------
    # Stage
    # -----------------------------------------------------

    stage = weekly_count + 1

    # -----------------------------------------------------
    # Save GENERATED message
    #
    # Important:
    # This does NOT mean it was actually sent yet.
    # -----------------------------------------------------

    nurture_record = NurtureMessage(
        lead_id=lead.id,
        message=message,
        stage=stage,
        status="generated",
    )

    db.add(nurture_record)
    db.commit()
    db.refresh(nurture_record)

    return {
        "eligible": True,
        "reason": "message_generated",
        "nurture_id": nurture_record.id,
        "lead_id": lead.id,
        "stage": stage,
        "messages_sent_this_week": weekly_count,
        "message": message,
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

    record = (
        db.query(NurtureMessage)
        .filter(
            NurtureMessage.id == nurture_id
        )
        .first()
    )

    if not record:
        return {
            "success": False,
            "reason": "nurture_message_not_found",
        }

    if record.status == "sent":
        return {
            "success": False,
            "reason": "already_sent",
        }

    record.status = "sent"
    record.sent_at = sent_time

    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "nurture_id": record.id,
        "lead_id": record.lead_id,
        "stage": record.stage,
        "sent_at": record.sent_at,
    }