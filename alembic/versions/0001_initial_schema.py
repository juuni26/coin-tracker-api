"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "coins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("market_cap_rank", sa.Integer(), nullable=True),
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("external_id", name="uq_coins_external_id"),
    )
    op.create_index("ix_coins_external_id", "coins", ["external_id"], unique=True)

    op.create_table(
        "portfolio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("coin_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["coin_id"], ["coins.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "coin_id", name="uq_portfolio_user_coin"),
    )
    op.create_index("ix_portfolio_user_id", "portfolio", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_user_id", table_name="portfolio")
    op.drop_table("portfolio")
    op.drop_index("ix_coins_external_id", table_name="coins")
    op.drop_table("coins")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
