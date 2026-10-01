"""oauth for mcp: apps that registered (Claude), authorization codes and tokens

Revision ID: 463489e14bd9
Revises: 525a0bd9e5e5
Create Date: 2026-10-01 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '463489e14bd9'
down_revision: Union[str, Sequence[str], None] = '525a0bd9e5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('oauth_client',
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.Column('info', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('client_id', name=op.f('pk_oauth_client'))
    )
    op.create_table('oauth_code',
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('redirect_uri', sa.Text(), nullable=False),
    sa.Column('redirect_uri_provided_explicitly', sa.Boolean(), nullable=False),
    sa.Column('code_challenge', sa.String(length=128), nullable=False),
    sa.Column('scopes', sa.Text(), nullable=False),
    sa.Column('resource', sa.Text(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], name=op.f('fk_oauth_code_client_id_oauth_client'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_oauth_code_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('code_hash', name=op.f('pk_oauth_code'))
    )
    op.create_table('oauth_token',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('grant', sa.String(length=64), nullable=False),
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('scopes', sa.Text(), nullable=False),
    sa.Column('resource', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], name=op.f('fk_oauth_token_client_id_oauth_client'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_oauth_token_user_id_app_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('token_hash', name=op.f('pk_oauth_token'))
    )
    op.create_index(op.f('ix_oauth_token_grant'), 'oauth_token', ['grant'], unique=False)
    op.create_index(op.f('ix_oauth_token_user_id'), 'oauth_token', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_oauth_token_user_id'), table_name='oauth_token')
    op.drop_index(op.f('ix_oauth_token_grant'), table_name='oauth_token')
    op.drop_table('oauth_token')
    op.drop_table('oauth_code')
    op.drop_table('oauth_client')
