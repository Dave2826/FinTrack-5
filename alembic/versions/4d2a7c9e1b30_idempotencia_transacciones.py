"""idempotencia de transacciones (Unidad III, Actividad 13)

Revision ID: 4d2a7c9e1b30
Revises: 3b9f41c7d2ae
Create Date: 2026-11-18 00:00:00.000000

Agrega la tabla idempotency_keys. No modifica ni borra filas existentes:
los movimientos, cuentas, conceptos y membresias quedan intactos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4d2a7c9e1b30'
down_revision: Union[str, Sequence[str], None] = '3b9f41c7d2ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('operation', sa.String(length=64), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('company_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.ForeignKeyConstraint(['company_user_id'], ['company_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'company_id',
            'operation',
            'idempotency_key',
            name='uq_idempotency_company_operation_key',
        ),
    )
    op.create_index(op.f('ix_idempotency_keys_id'), 'idempotency_keys', ['id'], unique=False)
    op.create_index(op.f('ix_idempotency_keys_transaction_id'), 'idempotency_keys', ['transaction_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_idempotency_keys_transaction_id'), table_name='idempotency_keys')
    op.drop_index(op.f('ix_idempotency_keys_id'), table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
