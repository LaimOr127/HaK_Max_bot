"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-21 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("investor_prompt_state", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("max_user_id"),
    )
    op.create_index("ix_users_last_seen_at", "users", ["last_seen_at"])

    op.create_table(
        "regions",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "sphere_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "measures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("support_level", sa.String(length=32), nullable=False),
        sa.Column("amount_display", sa.String(length=255), nullable=False),
        sa.Column("amount_min_rub", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("amount_max_rub", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("benefit_detail", sa.Text(), nullable=True),
        sa.Column("what_is_it", sa.Text(), nullable=False),
        sa.Column("who_can_receive", sa.Text(), nullable=False),
        sa.Column("where_to_apply", sa.Text(), nullable=False),
        sa.Column("review_days", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_checked_at", sa.Date(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("employee_min", sa.Integer(), nullable=True),
        sa.Column("employee_max", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_code"),
    )
    op.create_index("ix_measures_is_active", "measures", ["is_active"])
    op.create_index("ix_measures_application_deadline", "measures", ["application_deadline"])
    op.create_index("ix_measures_priority", "measures", ["priority"])
    op.create_index("ix_measures_amount_max_rub", "measures", ["amount_max_rub"])

    op.create_table(
        "conversation_states",
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("max_user_id"),
    )
    op.create_table(
        "okved_mappings",
        sa.Column("okved_class", sa.String(length=2), nullable=False),
        sa.Column("sphere_category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["sphere_category_id"], ["sphere_categories.id"]),
        sa.PrimaryKeyConstraint("okved_class"),
    )
    op.create_table(
        "company_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=True),
        sa.Column("company_name", sa.String(length=512), nullable=True),
        sa.Column("region_code", sa.String(length=16), nullable=True),
        sa.Column("primary_okved", sa.String(length=16), nullable=True),
        sa.Column("sphere_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("business_stage", sa.String(length=32), nullable=True),
        sa.Column("business_form", sa.String(length=16), nullable=True),
        sa.Column("employee_bucket", sa.String(length=32), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("msp_category", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fns_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_code"], ["regions.code"]),
        sa.ForeignKeyConstraint(["sphere_category_id"], ["sphere_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("max_user_id", name="uq_company_profiles_max_user_id"),
    )
    op.create_index("ix_company_profiles_inn", "company_profiles", ["inn"])

    op.create_table(
        "measure_regions",
        _id(),
        _measure_fk(),
        sa.Column("region_code", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["region_code"], ["regions.code"]),
        sa.UniqueConstraint("measure_id", "region_code", name="uq_measure_regions"),
    )
    op.create_table(
        "measure_spheres",
        _id(),
        _measure_fk(),
        sa.Column("sphere_category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["sphere_category_id"], ["sphere_categories.id"]),
        sa.UniqueConstraint("measure_id", "sphere_category_id", name="uq_measure_spheres"),
    )
    op.create_table(
        "measure_business_forms",
        _id(),
        _measure_fk(),
        sa.Column("business_form", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("measure_id", "business_form", name="uq_measure_forms"),
    )
    op.create_table(
        "measure_business_stages",
        _id(),
        _measure_fk(),
        sa.Column("business_stage", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("measure_id", "business_stage", name="uq_measure_stages"),
    )
    op.create_table(
        "measure_msp_categories",
        _id(),
        _measure_fk(),
        sa.Column("msp_category", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("measure_id", "msp_category", name="uq_measure_msp"),
    )

    op.create_table(
        "measure_documents",
        _id(),
        _measure_fk(),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.UniqueConstraint("measure_id", "code", name="uq_measure_documents_code"),
    )
    op.create_table(
        "user_measure_checklists",
        _id(),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        _measure_fk(),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("max_user_id", "measure_id", name="uq_user_measure_checklists"),
    )
    op.create_table(
        "courses",
        _id(),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("sphere_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sphere_category_id"], ["sphere_categories.id"]),
    )
    op.create_table(
        "measure_feedback",
        _id(),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        _measure_fk(),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "investor_leads",
        _id(),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("max_user_id"),
    )
    op.create_table(
        "usage_counters",
        sa.Column("measure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "checklist_add_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["measure_id"], ["measures.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("measure_id"),
    )
    op.create_table(
        "analytics_events",
        _id(),
        sa.Column("max_user_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("measure_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["measure_id"], ["measures.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_analytics_events_type_created", "analytics_events", ["event_type", "created_at"]
    )
    op.create_index(
        "ix_analytics_events_user_created", "analytics_events", ["max_user_id", "created_at"]
    )
    op.create_table(
        "reminder_deliveries",
        _id(),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        _measure_fk(),
        sa.Column("days_before", sa.Integer(), nullable=False),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("days_before > 0", name="ck_reminder_deliveries_days_positive"),
        sa.ForeignKeyConstraint(["max_user_id"], ["users.max_user_id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "max_user_id", "measure_id", "days_before", name="uq_reminder_deliveries"
        ),
    )
    op.create_table(
        "checklist_document_states",
        _id(),
        sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("measure_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_done", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["checklist_id"], ["user_measure_checklists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["measure_document_id"], ["measure_documents.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "checklist_id", "measure_document_id", name="uq_checklist_document_states"
        ),
    )


def downgrade() -> None:
    for table in (
        "checklist_document_states",
        "reminder_deliveries",
        "analytics_events",
        "usage_counters",
        "investor_leads",
        "measure_feedback",
        "courses",
        "user_measure_checklists",
        "measure_documents",
        "measure_msp_categories",
        "measure_business_stages",
        "measure_business_forms",
        "measure_spheres",
        "measure_regions",
        "company_profiles",
        "okved_mappings",
        "conversation_states",
        "measures",
        "sphere_categories",
        "regions",
        "users",
    ):
        op.drop_table(table)


def _id() -> sa.Column[sa.Uuid]:
    return sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True)


def _measure_fk() -> sa.Column[sa.Uuid]:
    return sa.Column(
        "measure_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("measures.id", ondelete="CASCADE"),
        nullable=False,
    )
