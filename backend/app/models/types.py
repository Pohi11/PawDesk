from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """A text column limited to the enum's values by a CHECK constraint (design D3).

    values_callable stores the lowercase values ("dog"), not the member names ("DOG").
    `name` becomes the CHECK constraint's name: ck_<table>_<name>.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())
