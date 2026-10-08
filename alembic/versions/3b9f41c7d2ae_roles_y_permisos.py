"""roles y permisos

Revision ID: 3b9f41c7d2ae
Revises: 2ceeae7ff07c
Create Date: 2026-10-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b9f41c7d2ae'
down_revision: Union[str, Sequence[str], None] = '2ceeae7ff07c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_role_code')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)

    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_permission_code')
    )
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'], unique=False)

    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission')
    )
    op.create_index(op.f('ix_role_permissions_id'), 'role_permissions', ['id'], unique=False)
    op.create_index(op.f('ix_role_permissions_role_id'), 'role_permissions', ['role_id'], unique=False)
    op.create_index(op.f('ix_role_permissions_permission_id'), 'role_permissions', ['permission_id'], unique=False)

    op.create_table(
        'company_user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['company_user_id'], ['company_users.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_user_id', 'role_id', name='uq_company_user_role')
    )
    op.create_index(op.f('ix_company_user_roles_id'), 'company_user_roles', ['id'], unique=False)
    op.create_index(op.f('ix_company_user_roles_company_user_id'), 'company_user_roles', ['company_user_id'], unique=False)
    op.create_index(op.f('ix_company_user_roles_role_id'), 'company_user_roles', ['role_id'], unique=False)
    op.create_index(
        'uq_company_user_role_active',
        'company_user_roles',
        ['company_user_id'],
        unique=True,
        postgresql_where=sa.text('is_active')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_company_user_role_active', table_name='company_user_roles')
    op.drop_index(op.f('ix_company_user_roles_role_id'), table_name='company_user_roles')
    op.drop_index(op.f('ix_company_user_roles_company_user_id'), table_name='company_user_roles')
    op.drop_index(op.f('ix_company_user_roles_id'), table_name='company_user_roles')
    op.drop_table('company_user_roles')

    op.drop_index(op.f('ix_role_permissions_permission_id'), table_name='role_permissions')
    op.drop_index(op.f('ix_role_permissions_role_id'), table_name='role_permissions')
    op.drop_index(op.f('ix_role_permissions_id'), table_name='role_permissions')
    op.drop_table('role_permissions')

    op.drop_index(op.f('ix_permissions_id'), table_name='permissions')
    op.drop_table('permissions')

    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles')
