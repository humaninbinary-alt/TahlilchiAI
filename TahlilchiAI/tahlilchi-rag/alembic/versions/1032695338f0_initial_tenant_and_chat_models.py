"""Initial tenant and chat models

Revision ID: 1032695338f0
Revises:
Create Date: 2025-11-19 15:01:47.391909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1032695338f0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_role enum type
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'manager', 'member')")

    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('default_language', sa.String(length=10), nullable=False, server_default=sa.text("'uz'")),
        sa.Column('allowed_features', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_tenants_slug'), 'tenants', ['slug'], unique=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'manager', 'member', name='user_role', create_type=False), nullable=False, server_default=sa.text("'member'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_tenant_id'), 'users', ['tenant_id'], unique=False)
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'], unique=True)

    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('purpose', sa.String(length=100), nullable=False),
        sa.Column('target_audience', sa.String(length=100), nullable=False),
        sa.Column('tone', sa.String(length=100), nullable=False),
        sa.Column('strictness', sa.String(length=100), nullable=False),
        sa.Column('sensitivity', sa.String(length=100), nullable=False),
        sa.Column('document_types', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('document_languages', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('embedding_model', sa.String(length=255), nullable=False, server_default=sa.text("'intfloat/multilingual-e5-large'")),
        sa.Column('llm_model', sa.String(length=255), nullable=False, server_default=sa.text("'qwen2.5:14b'")),
        sa.Column('retrieval_strategy', sa.String(length=100), nullable=False, server_default=sa.text("'hybrid'")),
        sa.Column('max_context_chunks', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chats_tenant_id'), 'chats', ['tenant_id'], unique=False)
    op.create_index('ix_chats_tenant_slug', 'chats', ['tenant_id', 'slug'], unique=True)

    # Create chat_access table
    op.create_table(
        'chat_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'chat_id', name='uq_user_chat_access')
    )
    op.create_index('ix_chat_access_tenant_id', 'chat_access', ['tenant_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_chat_access_tenant_id', table_name='chat_access')
    op.drop_table('chat_access')

    op.drop_index('ix_chats_tenant_slug', table_name='chats')
    op.drop_index(op.f('ix_chats_tenant_id'), table_name='chats')
    op.drop_table('chats')

    op.drop_index('ix_users_tenant_email', table_name='users')
    op.drop_index(op.f('ix_users_tenant_id'), table_name='users')
    op.drop_table('users')

    op.drop_index(op.f('ix_tenants_slug'), table_name='tenants')
    op.drop_table('tenants')

    # Drop enum type
    op.execute("DROP TYPE user_role")
