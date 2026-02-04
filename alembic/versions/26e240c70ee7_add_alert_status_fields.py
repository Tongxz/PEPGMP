"""add_alert_status_fields

Revision ID: 26e240c70ee7
Revises: de374ef6dace
Create Date: 2026-01-14 16:39:13.263796

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "26e240c70ee7"
down_revision: Union[str, Sequence[str], None] = "de374ef6dace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加告警状态字段
    op.add_column(
        "alert_history",
        sa.Column(
            "status",
            sa.String(20),
            nullable=True,
            server_default="pending",
            comment="告警状态: pending, confirmed, false_positive, resolved",
        ),
    )
    op.add_column(
        "alert_history",
        sa.Column(
            "handled_at",
            sa.DateTime(),
            nullable=True,
            comment="处理时间",
        ),
    )
    op.add_column(
        "alert_history",
        sa.Column(
            "handled_by",
            sa.String(100),
            nullable=True,
            comment="处理人",
        ),
    )
    # 创建索引以提高查询性能
    op.create_index(
        "ix_alert_history_status",
        "alert_history",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 删除索引
    op.drop_index("ix_alert_history_status", table_name="alert_history")
    # 删除字段
    op.drop_column("alert_history", "handled_by")
    op.drop_column("alert_history", "handled_at")
    op.drop_column("alert_history", "status")
