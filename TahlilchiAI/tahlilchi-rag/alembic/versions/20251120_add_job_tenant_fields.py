"""Add tenant-aware fields to jobs table.

Revision ID: job_multitenant_001
Revises: bm25_001
Create Date: 2025-11-20 00:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "job_multitenant_001"
down_revision: Union[str, None] = "bm25_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Jobs are ephemeral status records, so it's safe to truncate before altering schema.
    op.execute("TRUNCATE TABLE jobs")

    op.add_column(
        "jobs",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "chat_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_jobs_tenant_id",
        "jobs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_jobs_chat_id",
        "jobs",
        "chats",
        ["chat_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_jobs_created_by",
        "jobs",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_jobs_tenant_id", "jobs", ["tenant_id"], unique=False)
    op.create_index("ix_jobs_chat_id", "jobs", ["chat_id"], unique=False)
    op.create_index("ix_jobs_created_by", "jobs", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_created_by", table_name="jobs")
    op.drop_index("ix_jobs_chat_id", table_name="jobs")
    op.drop_index("ix_jobs_tenant_id", table_name="jobs")

    op.drop_constraint("fk_jobs_created_by", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_chat_id", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_tenant_id", "jobs", type_="foreignkey")

    op.drop_column("jobs", "created_by")
    op.drop_column("jobs", "chat_id")
    op.drop_column("jobs", "tenant_id")

