"""create audit tables

Revision ID: 0001
Revises:
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(16), nullable=False, server_default="system"),
        sa.Column("payload_json", sa.Text, nullable=False, server_default="{}"),
    )
    op.create_index("ix_audit_log_session_id", "audit_log", ["session_id"])

    op.create_table(
        "verified_interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("audio_hash", sa.String(64), nullable=True),
        sa.Column("asr_text", sa.Text, nullable=False, server_default=""),
        sa.Column("intent", sa.String(64), nullable=False, server_default="other_grievance"),
        sa.Column("dialect", sa.String(32), nullable=True),
        sa.Column("district", sa.String(64), nullable=False, server_default="default"),
        sa.Column("verification_state", sa.String(16), nullable=False),
        sa.Column("agent_corrections_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("final_intent", sa.String(64), nullable=True),
        sa.Column("composite_confidence", sa.Float, nullable=True),
        sa.Column("sentiment_label", sa.String(32), nullable=True),
        sa.Column("language", sa.String(8), nullable=False, server_default="kn"),
        sa.Column("clarification_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_escalated", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index(
        "ix_verified_interactions_session_id", "verified_interactions", ["session_id"]
    )


def downgrade() -> None:
    op.drop_table("verified_interactions")
    op.drop_table("audit_log")
