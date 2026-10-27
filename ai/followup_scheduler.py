
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import Lead, LeadActivity


def schedule_follow_up(
    db: Session,
    lead_id: int,
) -> dict:
    """
    Schedule a follow-up based on lead priority.
    This function schedules only; it does not send messages.
    """

    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id)
        .with_for_update()
        .first()
    )

    if not lead:
        return {
            "success": False,
            "reason": "lead_not_found",
            "lead_id": lead_id,
        }

    # Do not schedule follow-ups for closed leads.
    if (lead.status or "").lower() in {
        "closed",
        "converted",
        "lost",
    }:
        return {
            "success": False,
            "reason": "lead_not_active",
            "lead_id": lead_id,
        }

    # Prevent rescheduling an existing future follow-up.
    now = datetime.now(timezone.utc)
    existing = lead.follow_up_at

    if existing is not None:
        if existing.tzinfo is None:
            existing = existing.replace(tzinfo=timezone.utc)

        if existing > now:
            return {
                "success": True,
                "reason": "already_scheduled",
                "lead_id": lead.id,
                "follow_up_at": existing.isoformat(),
            }

    # Use the stronger of the business and AI scores.
    score = max(
        lead.lead_score or 0,
        lead.ai_score or 0,
    )

    temperature = max(
        [
            (lead.lead_temperature or "").lower(),
            (lead.ai_temperature or "").lower(),
        ],
        key=lambda value: {
            "hot": 3,
            "warm": 2,
            "cold": 1,
        }.get(value, 0),
    )

    if temperature == "hot" or score >= 75:
        delay = timedelta(hours=4)
        priority = "high"
    elif temperature == "warm" or score >= 40:
        delay = timedelta(days=1)
        priority = "medium"
    else:
        delay = timedelta(days=3)
        priority = "low"

    follow_up_at = now + delay
    lead.follow_up_at = follow_up_at

    db.add(
        LeadActivity(
            lead_id=lead.id,
            activity_type="follow_up_scheduled",
            description=(
                f"{priority.title()}-priority follow-up scheduled "
                f"for {follow_up_at.isoformat()}."
            ),
        )
    )

    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "reason": "follow_up_scheduled",
        "lead_id": lead.id,
        "priority": priority,
        "score": score,
        "follow_up_at": follow_up_at.isoformat(),
    }
