"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hotels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("star_rating", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_hotels_city", "hotels", ["city"])
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hotel_id", sa.Integer(), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("room_type", sa.String(50), nullable=False),
        sa.Column("cancellation_policy", sa.String(50), nullable=False),
        sa.Column("occupancy", sa.Integer(), server_default="2"),
    )
    op.create_index("ix_rooms_hotel_id", "rooms", ["hotel_id"])
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("markup_pct", sa.Float(), server_default="0"),
    )
    op.create_table(
        "exchange_rates",
        sa.Column("currency", sa.String(8), primary_key=True),
        sa.Column("rate_to_usd", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "rate_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("hotel_id", sa.Integer(), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("stay_date", sa.Date(), nullable=False),
        sa.Column("nights", sa.Integer(), server_default="1"),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("price_original", sa.Float(), nullable=False),
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("availability", sa.Integer(), nullable=False),
        sa.Column("occupancy", sa.Integer(), server_default="2"),
        sa.Column("cancellation_policy", sa.String(50), nullable=False),
        sa.Column("scenario", sa.String(32), server_default="NORMAL"),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", name="uq_rate_events_event_id"),
    )
    op.create_index("ix_rate_events_lookup", "rate_events", ["hotel_id", "room_id", "stay_date", "supplier_id", "received_at"])
    op.create_index("ix_rate_events_stay", "rate_events", ["stay_date"])
    op.create_index("ix_rate_events_city_received", "rate_events", ["city", "received_at"])
    op.create_index("ix_rate_events_received_at", "rate_events", ["received_at"])
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), server_default="OPEN"),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("hotel_id", sa.Integer(), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("stay_date", sa.Date(), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("supplier_codes", sa.JSON(), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_alerts_status_created", "alerts", ["status", "created_at"])
    op.create_index("ix_alerts_fingerprint", "alerts", ["fingerprint", "created_at"])
    op.create_index("ix_alerts_city_severity", "alerts", ["city", "severity"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_table(
        "dlq_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_dlq_events_event_id", "dlq_events", ["event_id"])
    op.create_index("ix_dlq_events_created_at", "dlq_events", ["created_at"])
    op.create_table(
        "daily_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("hotel_id", sa.Integer(), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("avg_price", sa.Float(), nullable=False),
        sa.Column("median_price", sa.Float(), nullable=False),
        sa.Column("volatility", sa.Float(), nullable=False),
        sa.Column("parity_violations", sa.Integer(), server_default="0"),
        sa.Column("demand_score", sa.Float(), server_default="0"),
        sa.Column("event_count", sa.Integer(), server_default="0"),
        sa.UniqueConstraint("stat_date", "hotel_id", name="uq_daily_stats_date_hotel"),
    )
    op.create_index("ix_daily_stats_stat_date", "daily_stats", ["stat_date"])
    op.create_index("ix_daily_stats_city", "daily_stats", ["city"])
    op.create_table(
        "system_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("value", sa.Float(), server_default="0"),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("system_metrics")
    op.drop_table("daily_stats")
    op.drop_table("dlq_events")
    op.drop_table("alerts")
    op.drop_table("rate_events")
    op.drop_table("exchange_rates")
    op.drop_table("suppliers")
    op.drop_table("rooms")
    op.drop_table("hotels")
