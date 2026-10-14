"""orchestration

Revision ID: cbd3fa08de3d
Revises: 967b1a9f9a08
Create Date: 2026-10-14

Certificate images attached to booking requests, and the saved result of each finished
orchestration step (the checkpoints a resumed run reads instead of redoing work).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "cbd3fa08de3d"
down_revision: str | Sequence[str] | None = "967b1a9f9a08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUIDV7 = sa.text("uuidv7()")
NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "booking_documents",
        sa.Column("id", sa.Uuid(), server_default=UUIDV7, nullable=False),
        sa.Column("booking_request_id", sa.Uuid(), nullable=False),
        sa.Column("mime", sa.String(length=32), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "mime IN ('image/png', 'image/jpeg', 'image/webp')",
            name=op.f("ck_booking_documents_supported_type"),
        ),
        sa.CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 5242880",
            name=op.f("ck_booking_documents_size_in_range"),
        ),
        sa.CheckConstraint(
            "size_bytes = octet_length(content)",
            name=op.f("ck_booking_documents_size_matches_content"),
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_booking_documents_sha256_is_hex")
        ),
        sa.ForeignKeyConstraint(
            ["booking_request_id"],
            ["booking_requests.id"],
            name=op.f("fk_booking_documents_booking_request_id_booking_requests"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_documents")),
        sa.UniqueConstraint(
            "booking_request_id", name=op.f("uq_booking_documents_booking_request_id")
        ),
    )
    op.create_table(
        "booking_step_results",
        sa.Column("id", sa.Uuid(), server_default=UUIDV7, nullable=False),
        sa.Column("booking_request_id", sa.Uuid(), nullable=False),
        sa.Column("step", sa.String(length=32), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "step IN ('intake', 'records', 'checks', 'route')",
            name=op.f("ck_booking_step_results_step"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(output) = 'object'", name=op.f("ck_booking_step_results_output_is_object")
        ),
        sa.ForeignKeyConstraint(
            ["booking_request_id"],
            ["booking_requests.id"],
            name=op.f("fk_booking_step_results_booking_request_id_booking_requests"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_booking_step_results")),
        sa.UniqueConstraint(
            "booking_request_id",
            "step",
            name=op.f("uq_booking_step_results_booking_request_id_step"),
        ),
    )


def downgrade() -> None:
    op.drop_table("booking_step_results")
    op.drop_table("booking_documents")
