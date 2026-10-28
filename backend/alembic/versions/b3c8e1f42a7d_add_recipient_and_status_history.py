"""add recipient and status history

Revision ID: b3c8e1f42a7d
Revises: fc11c9b21045
Create Date: 2026-10-28 10:46:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3c8e1f42a7d"
down_revision = "fc11c9b21045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add recipient columns to payment_orders
    op.add_column("payment_orders", sa.Column("recipient_identifier", sa.String(100), nullable=True))
    op.add_column("payment_orders", sa.Column("recipient_type", sa.String(20), nullable=True))
    op.add_column("payment_orders", sa.Column("recipient_display_name", sa.String(100), nullable=True))

    # Create payment_status_history table
    op.create_table(
        "payment_status_history",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("payment_order_id", sa.Uuid(as_uuid=False), sa.ForeignKey("payment_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_status", sa.String(20), nullable=False),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_payment_status_history_order_created",
        "payment_status_history",
        ["payment_order_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("payment_status_history")
    op.drop_column("payment_orders", "recipient_display_name")
    op.drop_column("payment_orders", "recipient_type")
    op.drop_column("payment_orders", "recipient_identifier")
