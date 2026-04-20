import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BlastRadiusConsumer(Base):
    __tablename__ = "blast_radius_consumers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    entity_fqn: Mapped[str] = mapped_column(String(512))
    entity_type: Mapped[str] = mapped_column(String(128))
    level: Mapped[int] = mapped_column(Integer)
    service: Mapped[str] = mapped_column(String(128))
