"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-13

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "PARENT", name="user_role"),
            nullable=False,
            server_default="PARENT",
        ),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "children",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("birthdate", sa.Date, nullable=False),
        sa.Column("grade", sa.Integer, nullable=True),
        sa.Column("locale", sa.String(16), nullable=False, server_default="hy-AM"),
        sa.Column("preferences", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_children_parent_id", "children", ["parent_id"])

    op.create_table(
        "age_bands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(60), nullable=False, unique=True),
        sa.Column("min_age", sa.Integer, nullable=False),
        sa.Column("max_age", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("pedagogy_notes", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "age_band_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("age_bands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(60), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
    )
    op.create_index("ix_courses_age_band_id", "courses", ["age_band_id"])

    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_units_course_id", "units", ["course_id"])

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("p_init", sa.Float, nullable=False, server_default="0.1"),
        sa.Column("p_transit", sa.Float, nullable=False, server_default="0.2"),
        sa.Column("p_slip", sa.Float, nullable=False, server_default="0.1"),
        sa.Column("p_guess", sa.Float, nullable=False, server_default="0.2"),
        sa.Column("prerequisites", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index("ix_skills_unit_id", "skills", ["unit_id"])
    op.create_index("ix_skills_unit_code", "skills", ["unit_id", "code"], unique=True)

    op.create_table(
        "exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum(
                "MULTIPLE_CHOICE",
                "FREE_RESPONSE",
                "DRAG_DROP",
                "SHORT_ANSWER",
                name="exercise_type",
            ),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("difficulty", sa.Integer, nullable=False, server_default="1"),
        sa.Column("locale", sa.String(16), nullable=False, server_default="hy-AM"),
    )
    op.create_index("ix_exercises_skill_id", "exercises", ["skill_id"])

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "child_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locale", sa.String(16), nullable=False, server_default="hy-AM"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_sessions_child_id", "sessions", ["child_id"])

    op.create_table(
        "turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hy_text_in", sa.Text, nullable=True),
        sa.Column("en_text_in", sa.Text, nullable=True),
        sa.Column("en_text_out", sa.Text, nullable=True),
        sa.Column("hy_text_out", sa.Text, nullable=True),
        sa.Column("viz_spec", postgresql.JSONB, nullable=True),
        sa.Column("stt_ms", sa.Integer, nullable=True),
        sa.Column("safety_in_ms", sa.Integer, nullable=True),
        sa.Column("translate_in_ms", sa.Integer, nullable=True),
        sa.Column("curriculum_ms", sa.Integer, nullable=True),
        sa.Column("tutor_ms", sa.Integer, nullable=True),
        sa.Column("solver_ms", sa.Integer, nullable=True),
        sa.Column("assessment_ms", sa.Integer, nullable=True),
        sa.Column("viz_ms", sa.Integer, nullable=True),
        sa.Column("speech_ms", sa.Integer, nullable=True),
        sa.Column("translate_out_ms", sa.Integer, nullable=True),
        sa.Column("safety_out_ms", sa.Integer, nullable=True),
        sa.Column("tts_first_byte_ms", sa.Integer, nullable=True),
        sa.Column("tts_total_ms", sa.Integer, nullable=True),
        sa.Column("e2e_ms", sa.Integer, nullable=True),
        sa.Column("tokens_in_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_out_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd_est", sa.Float, nullable=False, server_default="0"),
        sa.Column("fallbacks", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("agent_path", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("request_id", sa.String(40), nullable=True),
    )
    op.create_index("ix_turns_session_id", "turns", ["session_id"])
    op.create_index("ix_turns_request_id", "turns", ["request_id"])

    op.create_table(
        "masteries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "child_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("p_known", sa.Float, nullable=False, server_default="0.1"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_masteries_child_id", "masteries", ["child_id"])
    op.create_index("ix_masteries_skill_id", "masteries", ["skill_id"])
    op.create_index("ix_mastery_child_skill", "masteries", ["child_id", "skill_id"], unique=True)

    op.create_table(
        "review_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "child_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("easiness", sa.Float, nullable=False, server_default="2.5"),
        sa.Column("repetitions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_outcome", sa.String(20), nullable=True),
    )
    op.create_index("ix_review_queue_items_child_id", "review_queue_items", ["child_id"])
    op.create_index("ix_review_queue_items_skill_id", "review_queue_items", ["skill_id"])
    op.create_index("ix_review_queue_items_due_at", "review_queue_items", ["due_at"])
    op.create_index(
        "ix_review_child_skill",
        "review_queue_items",
        ["child_id", "skill_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("review_queue_items")
    op.drop_table("masteries")
    op.drop_table("turns")
    op.drop_table("sessions")
    op.drop_table("exercises")
    op.drop_table("skills")
    op.drop_table("units")
    op.drop_table("courses")
    op.drop_table("age_bands")
    op.drop_table("children")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS exercise_type")
    op.execute("DROP TYPE IF EXISTS user_role")
