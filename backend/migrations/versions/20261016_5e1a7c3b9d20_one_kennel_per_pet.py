"""one kennel per pet

Revision ID: 5e1a7c3b9d20
Revises: c5f45f82a873
Create Date: 2026-10-16

No two reservations for the same pet may share a night (change one-kennel-per-pet).
Existing overlaps are removed first, keeping each pet's earliest reservation (design D3);
all data is synthetic. Downgrade drops the constraint and does not restore those rows.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "5e1a7c3b9d20"
down_revision: str | Sequence[str] | None = "c5f45f82a873"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME = "ex_reservations_one_kennel_per_pet"


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM reservations later
        USING reservations earlier
        WHERE later.pet_id = earlier.pet_id
          AND (earlier.created_at, earlier.id) < (later.created_at, later.id)
          AND daterange(later.start_date, later.end_date, '[)')
              && daterange(earlier.start_date, earlier.end_date, '[)')
        """
    )
    # Raw SQL: Alembic's create_exclude_constraint can't take the daterange expression.
    op.execute(
        f"""
        ALTER TABLE reservations ADD CONSTRAINT {NAME}
        EXCLUDE USING gist (pet_id WITH =, daterange(start_date, end_date, '[)') WITH &&)
        """
    )


def downgrade() -> None:
    op.drop_constraint(NAME, "reservations")
