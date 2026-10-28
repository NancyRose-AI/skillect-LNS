
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


# =========================================================
# LEAD MODEL
# =========================================================

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    source = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="new")
    notes = Column(Text, nullable=True)
    follow_up_at = Column(DateTime(timezone=True), nullable=True)

    # Business scoring
    lead_score = Column(Integer, nullable=False, default=0)
    lead_temperature = Column(String(20), nullable=False, default="cold")

    # AI qualification data
    interest = Column(String(100), nullable=True)
    budget = Column(Integer, nullable=True)
    timeline = Column(String(100), nullable=True)
    requirement = Column(String(150), nullable=True)

    # AI scoring
    ai_score = Column(Integer, nullable=False, default=0)
    ai_temperature = Column(String(20), nullable=False, default="cold")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    activities = relationship(
        "LeadActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="lead",
        cascade="all, delete-orphan",
    )
    alerts = relationship(
        "Alert",
        back_populates="lead",
        cascade="all, delete-orphan",
    )


# =========================================================
# LEAD ACTIVITY MODEL
# =========================================================

class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lead = relationship("Lead", back_populates="activities")


# =========================================================
# CONVERSATION MODEL
# =========================================================

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lead = relationship("Lead", back_populates="conversations")


# =========================================================
# NURTURE MESSAGE MODEL
# PERSON-2 AUTOMATED COLD-LEAD NURTURING
# =========================================================

class NurtureMessage(Base):
    __tablename__ = "nurture_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message = Column(Text, nullable=False)
    stage = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="generated")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# =========================================================
# HOT LEAD ALERT MODEL
# =========================================================

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    lead_id = Column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alert_type = Column(
        String(50),
        nullable=False,
        default="hot_lead",
    )

    # =====================================================
    # ENGAGEMENT CONTENT TRACKING
    # =====================================================

    # Examples:
    # educational
    # career_tip
    # industry_update
    # newsletter
    # image
    # batch_update
    content_type = Column(
        String(30),
        nullable=True,
    )

    # Examples:
    # AWS Cloud Engineering
    # Azure Cloud Engineering
    # DevOps
    # Cloud Engineering
    topic = Column(
        String(100),
        nullable=True,
    )

    # =====================================================
    # NURTURE TRACKING
    # =====================================================

    message = Column(Text, nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default="active",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# =========================================================
# LEAD ALERT MODEL
# HOT LEAD / SALES ALERT TRACKING
# =========================================================

class LeadAlert(Base):
    __tablename__ = "lead_alerts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    lead_id = Column(
        Integer,
        ForeignKey(
            "leads.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # Examples:
    # hot_lead
    # follow_up_required
    alert_type = Column(
        String(50),
        nullable=False,
    )

    # Example:
    # Lead 54 became HOT and requires sales follow-up.
    message = Column(
        Text,
        nullable=False,
    )

    # Future values:
    # pending
    # acknowledged
    # handled
    status = Column(
        String(20),
        nullable=False,
        default="pending",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    reason = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    qualification_summary = Column(Text, nullable=True)

    lead = relationship("Lead", back_populates="alerts")
