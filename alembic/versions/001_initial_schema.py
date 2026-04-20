"""initial_schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-20 00:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_fqn", sa.String(length=512), nullable=False),
        sa.Column("test_case_fqn", sa.String(length=512), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PROCESSING", "COMPLETE", "FAILED", name="incident_status"),
            nullable=False,
        ),
        sa.Column("root_cause_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "confidence_label",
            sa.Enum("HIGH", "MEDIUM", "LOW", name="confidence_label"),
            nullable=False,
        ),
        sa.Column("evidence_chain", sa.JSON(), nullable=False),
        sa.Column("remediation_steps", sa.JSON(), nullable=False),
        sa.Column("raw_report", sa.JSON(), nullable=False),
        sa.Column("blast_radius_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("slack_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("om_incident_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_incidents_table_fqn", "incidents", ["table_fqn"])
    op.create_index("ix_incidents_triggered_at", "incidents", ["triggered_at"])

    op.create_table(
        "timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_fqn", sa.String(length=512), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
    )
    op.create_index("ix_timeline_events_incident_id", "timeline_events", ["incident_id"])

    op.create_table(
        "blast_radius_consumers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_fqn", sa.String(length=512), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("service", sa.String(length=128), nullable=False),
    )
    op.create_index(
        "ix_blast_radius_consumers_incident_id", "blast_radius_consumers", ["incident_id"]
    )

    op.create_table(
        "tool_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column(
            "called_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("input_args", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("iteration", sa.Integer(), nullable=False),
    )
    op.create_index("ix_tool_call_logs_incident_id", "tool_call_logs", ["incident_id"])


def downgrade() -> None:
    op.drop_index("ix_tool_call_logs_incident_id", table_name="tool_call_logs")
    op.drop_table("tool_call_logs")
    op.drop_index("ix_blast_radius_consumers_incident_id", table_name="blast_radius_consumers")
    op.drop_table("blast_radius_consumers")
    op.drop_index("ix_timeline_events_incident_id", table_name="timeline_events")
    op.drop_table("timeline_events")
    op.drop_index("ix_incidents_triggered_at", table_name="incidents")
    op.drop_index("ix_incidents_table_fqn", table_name="incidents")
    op.drop_table("incidents")
    op.execute("DROP TYPE confidence_label")
    op.execute("DROP TYPE incident_status")
