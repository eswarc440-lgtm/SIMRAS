"""Add operational workflow tables for authentication, inspections, maintenance, plans, notifications

Revision ID: 0006
Revises: 0005
Create Date: 2024-09-20 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename existing tables to legacy
    op.execute('ALTER TABLE inspections RENAME TO legacy_inspections')
    op.execute('ALTER TABLE maintenance RENAME TO legacy_maintenance')
    op.execute('ALTER TABLE defects RENAME TO legacy_defects')

    # Update foreign key in legacy_defects
    op.drop_constraint('defects_inspection_id_fkey', 'legacy_defects', type_='foreignkey')
    op.create_foreign_key(
        'legacy_defects_inspection_id_fkey',
        'legacy_defects', 'legacy_inspections',
        ['inspection_id'], ['id'],
        ondelete='CASCADE'
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('officer_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False, server_default='OFFICER'),
        sa.Column('department', sa.String(length=200), nullable=True),
        sa.Column('designation', sa.String(length=200), nullable=True),
        sa.Column('district', sa.String(length=120), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('officer_id')
    )
    op.create_index(op.f('ix_users_district'), 'users', ['district'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index(op.f('ix_user_sessions_session_token'), 'user_sessions', ['session_token'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)

    # Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)

    # Create login_audit table
    op.create_table(
        'login_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=30), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('failure_reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id', ondelete='SET NULL']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_audit_action'), 'login_audit', ['action'], unique=False)
    op.create_index(op.f('ix_login_audit_created_at'), 'login_audit', ['created_at'], unique=False)
    op.create_index(op.f('ix_login_audit_user_id'), 'login_audit', ['user_id'], unique=False)

    # Create role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('permission', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role', 'permission', 'resource')
    )
    op.create_index(op.f('ix_role_permissions_permission'), 'role_permissions', ['permission'], unique=False)
    op.create_index(op.f('ix_role_permissions_role'), 'role_permissions', ['role'], unique=False)

    # Create asset_assignments table
    op.create_table(
        'asset_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assignment_type', sa.String(length=50), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_assignments_asset_id'), 'asset_assignments', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_assignments_user_id'), 'asset_assignments', ['user_id'], unique=False)

    # Create asset_reviews table
    op.create_table(
        'asset_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=False),
        sa.Column('review_type', sa.String(length=50), nullable=False),
        sa.Column('inspection_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('condition', sa.String(length=30), nullable=True),
        sa.Column('observation', sa.Text(), nullable=True),
        sa.Column('components_inspected', postgresql.JSONB(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(length=30), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_reviews_asset_id'), 'asset_reviews', ['asset_id'], unique=False)

    # Create new inspections table
    op.create_table(
        'inspections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(length=50), nullable=False),
        sa.Column('inspection_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('inspection_agency', sa.String(length=200), nullable=True),
        sa.Column('inspection_type', sa.String(length=50), nullable=False),
        sa.Column('assigned_officer', sa.Integer(), nullable=True),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='SCHEDULED'),
        sa.Column('deck_condition', sa.String(length=30), nullable=True),
        sa.Column('superstructure_condition', sa.String(length=30), nullable=True),
        sa.Column('substructure_condition', sa.String(length=30), nullable=True),
        sa.Column('foundation_condition', sa.String(length=30), nullable=True),
        sa.Column('scour_condition', sa.String(length=30), nullable=True),
        sa.Column('bearing_condition', sa.String(length=30), nullable=True),
        sa.Column('joint_condition', sa.String(length=30), nullable=True),
        sa.Column('overall_condition', sa.String(length=30), nullable=True),
        sa.Column('defect_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_defect_severity', sa.String(length=30), nullable=True),
        sa.Column('observation', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('verification_status', sa.String(length=30), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_officer'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspections_asset_code'), 'inspections', ['asset_code'], unique=False)
    op.create_index(op.f('ix_inspections_asset_id'), 'inspections', ['asset_id'], unique=False)
    op.create_index(op.f('ix_inspection_due_date'), 'inspections', ['due_date'], unique=False)
    op.create_index(op.f('ix_inspection_inspection_date'), 'inspections', ['inspection_date'], unique=False)
    op.create_index(op.f('ix_inspection_priority'), 'inspections', ['priority'], unique=False)
    op.create_index(op.f('ix_inspection_status'), 'inspections', ['status'], unique=False)

    # Create inspection_components table
    op.create_table(
        'inspection_components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inspection_id', sa.Integer(), nullable=False),
        sa.Column('component_name', sa.String(length=100), nullable=False),
        sa.Column('component_type', sa.String(length=50), nullable=False),
        sa.Column('condition', sa.String(length=30), nullable=True),
        sa.Column('observation', sa.Text(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_components_inspection_id'), 'inspection_components', ['inspection_id'], unique=False)

    # Create inspection_defects table
    op.create_table(
        'inspection_defects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inspection_id', sa.Integer(), nullable=False),
        sa.Column('component_id', sa.Integer(), nullable=True),
        sa.Column('defect_type', sa.String(length=80), nullable=False),
        sa.Column('severity', sa.String(length=30), nullable=False),
        sa.Column('measurement', postgresql.JSONB(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('observation', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['component_id'], ['inspection_components.id']),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_defects_inspection_id'), 'inspection_defects', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_inspection_defects_severity'), 'inspection_defects', ['severity'], unique=False)

    # Create inspection_documents table
    op.create_table(
        'inspection_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inspection_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('checksum', sa.String(length=128), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_documents_inspection_id'), 'inspection_documents', ['inspection_id'], unique=False)

    # Create inspection_assignments table
    op.create_table(
        'inspection_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inspection_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assignment_type', sa.String(length=50), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inspection_assignments_inspection_id'), 'inspection_assignments', ['inspection_id'], unique=False)

    # Create new maintenance table
    op.create_table(
        'maintenance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(length=50), nullable=False),
        sa.Column('maintenance_type', sa.String(length=50), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PROPOSED'),
        sa.Column('problem', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('proposed_action', sa.Text(), nullable=True),
        sa.Column('assigned_department', sa.String(length=200), nullable=True),
        sa.Column('contractor', sa.String(length=200), nullable=True),
        sa.Column('estimated_cost', sa.Integer(), nullable=True),
        sa.Column('actual_cost', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completion_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('related_inspection_id', sa.Integer(), nullable=True),
        sa.Column('related_plan_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('verification_status', sa.String(length=30), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['related_inspection_id'], ['inspections.id']),
        sa.ForeignKeyConstraint(['related_plan_id'], ['asset_plans.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_asset_code'), 'maintenance', ['asset_code'], unique=False)
    op.create_index(op.f('ix_maintenance_asset_id'), 'maintenance', ['asset_id'], unique=False)
    op.create_index(op.f('ix_maintenance_due_date'), 'maintenance', ['due_date'], unique=False)
    op.create_index(op.f('ix_maintenance_maintenance_type'), 'maintenance', ['maintenance_type'], unique=False)
    op.create_index(op.f('ix_maintenance_priority'), 'maintenance', ['priority'], unique=False)
    op.create_index(op.f('ix_maintenance_status'), 'maintenance', ['status'], unique=False)

    # Create maintenance_documents table
    op.create_table(
        'maintenance_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('maintenance_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('checksum', sa.String(length=128), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_documents_maintenance_id'), 'maintenance_documents', ['maintenance_id'], unique=False)

    # Create maintenance_progress table
    op.create_table(
        'maintenance_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('maintenance_id', sa.Integer(), nullable=False),
        sa.Column('progress_percentage', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_progress_maintenance_id'), 'maintenance_progress', ['maintenance_id'], unique=False)

    # Create maintenance_components table
    op.create_table(
        'maintenance_components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('maintenance_id', sa.Integer(), nullable=False),
        sa.Column('component_name', sa.String(length=100), nullable=False),
        sa.Column('component_type', sa.String(length=50), nullable=False),
        sa.Column('work_description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_components_maintenance_id'), 'maintenance_components', ['maintenance_id'], unique=False)

    # Create asset_plans table
    op.create_table(
        'asset_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_number', sa.String(length=50), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(length=50), nullable=False),
        sa.Column('plan_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default='MEDIUM'),
        sa.Column('problem_identified', sa.Text(), nullable=True),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('proposed_action', sa.Text(), nullable=True),
        sa.Column('affected_components', postgresql.JSONB(), nullable=True),
        sa.Column('proposed_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('proposed_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_cost', sa.Integer(), nullable=True),
        sa.Column('department', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_number')
    )
    op.create_index(op.f('ix_asset_plans_asset_code'), 'asset_plans', ['asset_code'], unique=False)
    op.create_index(op.f('ix_asset_plans_asset_id'), 'asset_plans', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_plans_plan_type'), 'asset_plans', ['plan_type'], unique=False)
    op.create_index(op.f('ix_asset_plans_priority'), 'asset_plans', ['priority'], unique=False)
    op.create_index(op.f('ix_asset_plans_status'), 'asset_plans', ['status'], unique=False)

    # Create plan_status_history table
    op.create_table(
        'plan_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(length=30), nullable=True),
        sa.Column('new_status', sa.String(length=30), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['asset_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plan_status_history_plan_id'), 'plan_status_history', ['plan_id'], unique=False)

    # Create plan_documents table
    op.create_table(
        'plan_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('checksum', sa.String(length=128), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['asset_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plan_documents_plan_id'), 'plan_documents', ['plan_id'], unique=False)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=30), nullable=False, server_default='INFO'),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('inspection_id', sa.Integer(), nullable=True),
        sa.Column('maintenance_id', sa.Integer(), nullable=True),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('link', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id']),
        sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['asset_plans.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_severity'), 'notifications', ['severity'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('before_state', postgresql.JSONB(), nullable=True),
        sa.Column('after_state', postgresql.JSONB(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id', ondelete='SET NULL']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_created_at'), 'audit_log', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_log_entity'), 'audit_log', ['entity_type', 'entity_id'], unique=False)
    op.create_index(op.f('ix_audit_log_user_action'), 'audit_log', ['user_id', 'action'], unique=False)
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'], unique=False)

    # Create ai_assistant_audit table
    op.create_table(
        'ai_assistant_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('asset_code', sa.String(length=50), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('assessment_id', sa.String(length=100), nullable=True),
        sa.Column('evidence_ids', postgresql.JSONB(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id', ondelete='SET NULL']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_assistant_audit_asset_code'), 'ai_assistant_audit', ['asset_code'], unique=False)
    op.create_index(op.f('ix_ai_assistant_audit_timestamp'), 'ai_assistant_audit', ['timestamp'], unique=False)
    op.create_index(op.f('ix_ai_assistant_audit_user_id'), 'ai_assistant_audit', ['user_id'], unique=False)

    # Create evidence_revisions table
    op.create_table(
        'evidence_revisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=120), nullable=False),
        sa.Column('old_value', postgresql.JSONB(), nullable=True),
        sa.Column('new_value', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('submitted_by', sa.Integer(), nullable=False),
        sa.Column('review_status', sa.String(length=30), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_revisions_asset_id'), 'evidence_revisions', ['asset_id'], unique=False)
    op.create_index(op.f('ix_evidence_revisions_field_name'), 'evidence_revisions', ['field_name'], unique=False)


def downgrade() -> None:
    # Drop new tables in reverse order
    op.drop_table('evidence_revisions')
    op.drop_table('ai_assistant_audit')
    op.drop_table('audit_log')
    op.drop_table('notifications')
    op.drop_table('plan_documents')
    op.drop_table('plan_status_history')
    op.drop_table('asset_plans')
    op.drop_table('maintenance_components')
    op.drop_table('maintenance_progress')
    op.drop_table('maintenance_documents')
    op.drop_table('maintenance')
    op.drop_table('inspection_assignments')
    op.drop_table('inspection_documents')
    op.drop_table('inspection_defects')
    op.drop_table('inspection_components')
    op.drop_table('inspections')
    op.drop_table('asset_reviews')
    op.drop_table('asset_assignments')
    op.drop_table('role_permissions')
    op.drop_table('login_audit')
    op.drop_table('password_reset_tokens')
    op.drop_table('user_sessions')
    op.drop_table('users')

    # Restore legacy tables
    op.execute('ALTER TABLE legacy_inspections RENAME TO inspections')
    op.execute('ALTER TABLE legacy_maintenance RENAME TO maintenance')
    op.execute('ALTER TABLE legacy_defects RENAME TO defects')

    # Restore foreign key
    op.drop_constraint('legacy_defects_inspection_id_fkey', 'defects', type_='foreignkey')
    op.create_foreign_key(
        'defects_inspection_id_fkey',
        'defects', 'inspections',
        ['inspection_id'], ['id'],
        ondelete='CASCADE'
    )
