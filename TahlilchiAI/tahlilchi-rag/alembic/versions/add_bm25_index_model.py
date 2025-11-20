"""Add bm25_index model

Revision ID: bm25_001
Revises: 0ee36bc30dc8
Create Date: 2025-11-19 06:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bm25_001'
down_revision: Union[str, None] = '0ee36bc30dc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bm25_indexes table
    op.create_table(
        'bm25_indexes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('corpus_tokens', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('doc_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('doc_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bm25_indexes_tenant_id'), 'bm25_indexes', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_bm25_indexes_chat_id'), 'bm25_indexes', ['chat_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_bm25_indexes_chat_id'), table_name='bm25_indexes')
    op.drop_index(op.f('ix_bm25_indexes_tenant_id'), table_name='bm25_indexes')
    op.drop_table('bm25_indexes')
