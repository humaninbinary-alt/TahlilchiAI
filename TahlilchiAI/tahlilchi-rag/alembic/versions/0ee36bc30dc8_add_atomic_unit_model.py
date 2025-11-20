"""Add atomic_unit model

Revision ID: 0ee36bc30dc8
Revises: 9e30551792f0
Create Date: 2025-11-19 15:49:41.268124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0ee36bc30dc8'
down_revision: Union[str, None] = '9e30551792f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create atomic_units table
    op.create_table(
        'atomic_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('unit_type', sa.String(length=50), nullable=False, comment='Type: section, paragraph, heading, table_row, list_item'),
        sa.Column('text', sa.Text(), nullable=False, comment='The actual content'),
        sa.Column('sequence', sa.Integer(), nullable=False, comment='Order within document (0, 1, 2...)'),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Parent unit for hierarchical structure'),
        sa.Column('level', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='Nesting level: 0=top, 1=sub, 2=paragraph...'),
        sa.Column('page_number', sa.Integer(), nullable=True, comment='Page number (for PDFs)'),
        sa.Column('section_title', sa.String(length=500), nullable=True, comment='Section/chapter title for context'),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'"), comment='Flexible metadata storage'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['atomic_units.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_atomic_units_chat_id'), 'atomic_units', ['chat_id'], unique=False)
    op.create_index(op.f('ix_atomic_units_document_id'), 'atomic_units', ['document_id'], unique=False)
    op.create_index(op.f('ix_atomic_units_tenant_id'), 'atomic_units', ['tenant_id'], unique=False)
    op.create_index('ix_atomic_units_document_sequence', 'atomic_units', ['document_id', 'sequence'], unique=False)
    op.create_index('ix_atomic_units_tenant_chat', 'atomic_units', ['tenant_id', 'chat_id'], unique=False)
    op.create_index('ix_atomic_units_tenant_document', 'atomic_units', ['tenant_id', 'document_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_atomic_units_tenant_document', table_name='atomic_units')
    op.drop_index('ix_atomic_units_tenant_chat', table_name='atomic_units')
    op.drop_index('ix_atomic_units_document_sequence', table_name='atomic_units')
    op.drop_index(op.f('ix_atomic_units_tenant_id'), table_name='atomic_units')
    op.drop_index(op.f('ix_atomic_units_document_id'), table_name='atomic_units')
    op.drop_index(op.f('ix_atomic_units_chat_id'), table_name='atomic_units')

    # Drop table
    op.drop_table('atomic_units')
