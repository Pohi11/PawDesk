"""reply and outbound messages

Revision ID: c5f45f82a873
Revises: 1311930054ec
Create Date: 2026-10-14

The message sent for each request (one per request), and `reply` joins the step names.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5f45f82a873"
down_revision: str | Sequence[str] | None = "1311930054ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STEP_CHECK = "ck_booking_step_results_step"
STEPS = "'intake', 'records', 'checks', 'route', 'resolution'"


def upgrade() -> None:
    op.create_table(
        "outbound_messages",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("booking_request_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('reply', 'decline')", name=op.f("ck_outbound_messages_kind_known")
        ),
        sa.CheckConstraint("btrim(body) <> ''", name=op.f("ck_outbound_messages_body_not_blank")),
        sa.ForeignKeyConstraint(
            ["booking_request_id"],
            ["booking_requests.id"],
            name=op.f("fk_outbound_messages_booking_request_id_booking_requests"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbound_messages")),
        sa.UniqueConstraint(
            "booking_request_id", name=op.f("uq_outbound_messages_booking_request_id")
        ),
    )
    op.drop_constraint(op.f(STEP_CHECK), "booking_step_results", type_="check")
    op.create_check_constraint(
        op.f(STEP_CHECK), "booking_step_results", f"step IN ({STEPS}, 'reply')"
    )


def downgrade() -> None:
    # The old constraint can't hold reply rows, so they go with it.
    op.execute("DELETE FROM booking_step_results WHERE step = 'reply'")
    op.drop_constraint(op.f(STEP_CHECK), "booking_step_results", type_="check")
    op.create_check_constraint(op.f(STEP_CHECK), "booking_step_results", f"step IN ({STEPS})")
    op.drop_table("outbound_messages")
