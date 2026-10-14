"""resolution step

Revision ID: 1311930054ec
Revises: cbd3fa08de3d
Create Date: 2026-10-14

Allow the resolver's saved result: `resolution` joins the step names.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "1311930054ec"
down_revision: str | Sequence[str] | None = "cbd3fa08de3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME = "ck_booking_step_results_step"


def upgrade() -> None:
    op.drop_constraint(op.f(NAME), "booking_step_results", type_="check")
    op.create_check_constraint(
        op.f(NAME),
        "booking_step_results",
        "step IN ('intake', 'records', 'checks', 'route', 'resolution')",
    )


def downgrade() -> None:
    # The old constraint can't hold resolution rows, so they go with it.
    op.execute("DELETE FROM booking_step_results WHERE step = 'resolution'")
    op.drop_constraint(op.f(NAME), "booking_step_results", type_="check")
    op.create_check_constraint(
        op.f(NAME), "booking_step_results", "step IN ('intake', 'records', 'checks', 'route')"
    )
