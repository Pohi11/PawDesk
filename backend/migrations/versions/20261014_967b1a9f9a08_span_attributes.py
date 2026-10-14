"""span attributes

Revision ID: 967b1a9f9a08
Revises: 25313e28dccb
Create Date: 2026-10-14

OpenTelemetry-style span attributes: a JSON object, empty by default.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "967b1a9f9a08"
down_revision: str | Sequence[str] | None = "25313e28dccb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "spans",
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_spans_attributes_is_object"), "spans", "jsonb_typeof(attributes) = 'object'"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_spans_attributes_is_object"), "spans", type_="check")
    op.drop_column("spans", "attributes")
