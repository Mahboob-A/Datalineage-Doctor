import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncidentStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ConfidenceLabel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_fqn: Mapped[str] = mapped_column(String(512), index=True)
    test_case_fqn: Mapped[str] = mapped_column(String(512))
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"), default=IncidentStatus.PROCESSING
    )
    root_cause_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_label: Mapped[ConfidenceLabel] = mapped_column(
        Enum(ConfidenceLabel, name="confidence_label"), default=ConfidenceLabel.LOW
    )
    evidence_chain: Mapped[list[str]] = mapped_column(JSON, default=list)
    remediation_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_report: Mapped[dict] = mapped_column(JSON, default=dict)
    blast_radius_count: Mapped[int] = mapped_column(Integer, default=0)
    slack_notified: Mapped[bool] = mapped_column(default=False)
    om_incident_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
