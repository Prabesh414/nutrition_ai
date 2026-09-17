"""Upgrade a legacy pre-JWT database in place.

Revision ID: 9c2f4a1b7e30
Revises: 8db187d5ede7
Create Date: 2026-09-16

The baseline revision creates the schema from nothing, which is what a fresh
database needs. A database created before this refactor already has all four
tables but is missing the columns added since:

    meal_logs.log_date      the calendar day a meal counts towards
    meal_logs.fiber         tracked per meal
    profiles.updated_at     last profile write

Without them every daily-scoped query fails, because `create_all()` only
creates missing *tables* and never alters an existing one.

Each step checks the live schema first, so this revision is safe to run
against a database that already has some or all of the columns -- including
one built by the baseline revision, where it is a no-op.

Existing meal rows are backfilled from `logged_at` so historical meals land on
the day they were recorded rather than collapsing onto today.
"""
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "9c2f4a1b7e30"
down_revision = "8db187d5ede7"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    meal_columns = _columns("meal_logs")

    if meal_columns and "fiber" not in meal_columns:
        # A constant server_default is allowed by SQLite's ALTER and fills
        # existing rows at the point the column is created.
        op.add_column(
            "meal_logs", sa.Column("fiber", sa.Float(), nullable=True, server_default="0.0")
        )

    if meal_columns and "log_date" not in meal_columns:
        # Added nullable so existing rows can be backfilled before the
        # NOT NULL constraint is applied.
        op.add_column("meal_logs", sa.Column("log_date", sa.Date(), nullable=True))

        # Derive the calendar day from the existing timestamp; fall back to
        # today for any row without one.
        if bind.dialect.name == "postgresql":
            op.execute(
                "UPDATE meal_logs SET log_date = COALESCE(logged_at::date, CURRENT_DATE) "
                "WHERE log_date IS NULL"
            )
        else:
            op.execute(
                "UPDATE meal_logs SET log_date = COALESCE(date(logged_at), date('now')) "
                "WHERE log_date IS NULL"
            )

        op.execute(
            sa.text("UPDATE meal_logs SET log_date = :today WHERE log_date IS NULL").bindparams(
                today=date.today()
            )
        )

        with op.batch_alter_table("meal_logs") as batch:
            batch.alter_column("log_date", existing_type=sa.Date(), nullable=False)

    if meal_columns:
        existing = _indexes("meal_logs")
        if "ix_meal_logs_log_date" not in existing:
            op.create_index("ix_meal_logs_log_date", "meal_logs", ["log_date"])
        if "ix_meal_logs_user_date" not in existing:
            op.create_index("ix_meal_logs_user_date", "meal_logs", ["user_id", "log_date"])

    profile_columns = _columns("profiles")
    if profile_columns and "updated_at" not in profile_columns:
        if bind.dialect.name == "postgresql":
            op.add_column(
                "profiles",
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            )
        else:
            # SQLite refuses ALTER TABLE ... ADD COLUMN with a non-constant
            # default, so add it bare and backfill.
            op.add_column("profiles", sa.Column("updated_at", sa.DateTime(timezone=True)))
            op.execute("UPDATE profiles SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

    # Dietary flags are indexed now because preference filters every
    # recommendation query.
    if _columns("food_items"):
        food_indexes = _indexes("food_items")
        if "ix_food_items_is_vegetarian" not in food_indexes:
            op.create_index("ix_food_items_is_vegetarian", "food_items", ["is_vegetarian"])
        if "ix_food_items_is_vegan" not in food_indexes:
            op.create_index("ix_food_items_is_vegan", "food_items", ["is_vegan"])

    # Final backfill pass. Run last and unconditionally, because a batch
    # table-rebuild earlier in this revision can reinstate NULLs written by an
    # UPDATE that preceded it. Touches only NULL rows, so it is idempotent.
    if "fiber" in _columns("meal_logs"):
        op.execute("UPDATE meal_logs SET fiber = 0.0 WHERE fiber IS NULL")


def downgrade() -> None:
    for table, index in (
        ("food_items", "ix_food_items_is_vegan"),
        ("food_items", "ix_food_items_is_vegetarian"),
        ("meal_logs", "ix_meal_logs_user_date"),
        ("meal_logs", "ix_meal_logs_log_date"),
    ):
        if index in _indexes(table):
            op.drop_index(index, table_name=table)

    if "updated_at" in _columns("profiles"):
        op.drop_column("profiles", "updated_at")

    if "log_date" in _columns("meal_logs"):
        op.drop_column("meal_logs", "log_date")

    if "fiber" in _columns("meal_logs"):
        op.drop_column("meal_logs", "fiber")
