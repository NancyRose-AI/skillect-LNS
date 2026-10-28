
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Lead, LeadActivity


def process_due_follow_ups(
    db: Session,
    limit: int = 100,
) -> dict:
    """
    Find due follow-ups and record each due action once.

    Safe mode:
    - Does not send WhatsApp messages.
    - Does not contact leads.
    - Records due actions in lead activity history.
    """

    now = datetime.now(timezone.utc)

    try:
        due_leads = (
            db.query(Lead)
            .filter(
                Lead.follow_up_at.isnot(None),
                Lead.follow_up_at <= now,
            )
            .order_by(Lead.follow_up_at.asc())
            .limit(limit)
            .all()
        )

        processed = []
        skipped = []

        for lead in due_leads:
            status = (lead.status or "").lower()

            if status in {"closed", "converted", "lost"}:
                skipped.append({
                    "lead_id": lead.id,
                    "reason": "lead_not_active",
                })
                continue

            scheduled_at = lead.follow_up_at

            # Prevent processing the same scheduled follow-up twice.
            existing_action = (
                db.query(LeadActivity)
                .filter(
                    LeadActivity.lead_id == lead.id,
                    LeadActivity.activity_type == "follow_up_due",
                    LeadActivity.created_at >= scheduled_at,
                )
                .first()
            )

            if existing_action:
                skipped.append({
                    "lead_id": lead.id,
                    "reason": "already_processed",
                })
                continue

            db.add(
                LeadActivity(
                    lead_id=lead.id,
                    activity_type="follow_up_due",
                    description=(
                        "Scheduled follow-up is due. "
                        "Ready for the next follow-up action. "
                        f"Scheduled time: {scheduled_at.isoformat()}"
                    ),
                )
            )

            processed.append({
                "lead_id": lead.id,
                "name": lead.name,
                "scheduled_at": scheduled_at.isoformat(),
                "action": "follow_up_due",
            })

        db.commit()

        return {
            "success": True,
            "checked_at": now.isoformat(),
            "checked_count": len(due_leads),
            "processed_count": len(processed),
            "processed": processed,
            "skipped": skipped,
            "message": (
                "Due follow-ups checked. "
                "No messages were sent."
            ),
        }

    except Exception:
        db.rollback()
        raise
