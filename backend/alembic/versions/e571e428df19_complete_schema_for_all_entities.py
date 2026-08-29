"""Complete schema for all entities (maintenance_logs, review_queue_items, analytics columns)

Revision ID: e571e428df19
Revises: 'ca1c2ccc9e79'
Create Date: 2026-08-30 01:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.models.base


# revision identifiers, used by Alembic.
revision: str = 'e571e428df19'
down_revision: Union[str, None] = 'ca1c2ccc9e79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create maintenance_logs table
    op.create_table(
        'maintenance_logs',
        sa.Column('id', app.models.base.GUID(length=36), nullable=False),
        sa.Column('cse_id', app.models.base.GUID(length=36), nullable=False),
        sa.Column('asset_id', app.models.base.GUID(length=36), nullable=True),
        sa.Column('maintenance_ref', sa.String(length=100), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cse_id'], ['cses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_maintenance_logs_asset_id'), 'maintenance_logs', ['asset_id'], unique=False)
    op.create_index(op.f('ix_maintenance_logs_created_at'), 'maintenance_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_maintenance_logs_cse_id'), 'maintenance_logs', ['cse_id'], unique=False)

    # 2. Create review_queue_items table
    op.create_table(
        'review_queue_items',
        sa.Column('id', app.models.base.GUID(length=36), nullable=False),
        sa.Column('analysis_run_id', app.models.base.GUID(length=36), nullable=False),
        sa.Column('finding_id', app.models.base.GUID(length=36), nullable=False),
        sa.Column('cse_id', app.models.base.GUID(length=36), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('priority_band', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Enum('NEW', 'IN_REVIEW', 'ESCALATED', 'DISMISSED', 'RESOLVED', name='queueitemstatus', native_enum=False), nullable=False, server_default='NEW'),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('contributing_factors', sa.JSON(), nullable=False),
        sa.Column('explanation_json', sa.JSON(), nullable=False),
        sa.Column('diversity_notes', sa.Text(), nullable=True),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['analysis_run_id'], ['analysis_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cse_id'], ['cses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('analysis_run_id', 'rank', name='uq_run_rank')
    )
    op.create_index(op.f('ix_review_queue_items_analysis_run_id'), 'review_queue_items', ['analysis_run_id'], unique=False)
    op.create_index(op.f('ix_review_queue_items_created_at'), 'review_queue_items', ['created_at'], unique=False)
    op.create_index(op.f('ix_review_queue_items_cse_id'), 'review_queue_items', ['cse_id'], unique=False)
    op.create_index(op.f('ix_review_queue_items_finding_id'), 'review_queue_items', ['finding_id'], unique=False)
    op.create_index(op.f('ix_review_queue_items_priority_band'), 'review_queue_items', ['priority_band'], unique=False)
    op.create_index(op.f('ix_review_queue_items_priority_score'), 'review_queue_items', ['priority_score'], unique=False)
    op.create_index(op.f('ix_review_queue_items_rank'), 'review_queue_items', ['rank'], unique=False)
    op.create_index(op.f('ix_review_queue_items_status'), 'review_queue_items', ['status'], unique=False)

    # 3. Add column to findings
    op.add_column('findings', sa.Column('evidence_completeness', sa.Float(), nullable=False, server_default='100.0'))

    # 4. Add columns to risk_scores
    op.add_column('risk_scores', sa.Column('raw_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('risk_scores', sa.Column('normalized_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('risk_scores', sa.Column('risk_band', sa.String(length=20), nullable=False, server_default='LOW'))
    op.add_column('risk_scores', sa.Column('overall_confidence', sa.Float(), nullable=False, server_default='1.0'))
    op.add_column('risk_scores', sa.Column('contributing_finding_ids', sa.JSON(), nullable=True))
    op.add_column('risk_scores', sa.Column('explanation_json', sa.JSON(), nullable=True))
    op.add_column('risk_scores', sa.Column('provenance_json', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_risk_scores_normalized_score'), 'risk_scores', ['normalized_score'], unique=False)
    op.create_index(op.f('ix_risk_scores_risk_band'), 'risk_scores', ['risk_band'], unique=False)

    # 5. Add columns to evidence
    op.add_column('evidence', sa.Column('evidence_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evidence', sa.Column('relevance', sa.Float(), nullable=False, server_default='1.0'))
    op.add_column('evidence', sa.Column('payload_json', sa.JSON(), nullable=True))
    op.add_column('evidence', sa.Column('provenance_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('evidence', 'provenance_json')
    op.drop_column('evidence', 'payload_json')
    op.drop_column('evidence', 'relevance')
    op.drop_column('evidence', 'evidence_timestamp')

    op.drop_index(op.f('ix_risk_scores_risk_band'), table_name='risk_scores')
    op.drop_index(op.f('ix_risk_scores_normalized_score'), table_name='risk_scores')
    op.drop_column('risk_scores', 'provenance_json')
    op.drop_column('risk_scores', 'explanation_json')
    op.drop_column('risk_scores', 'contributing_finding_ids')
    op.drop_column('risk_scores', 'overall_confidence')
    op.drop_column('risk_scores', 'risk_band')
    op.drop_column('risk_scores', 'normalized_score')
    op.drop_column('risk_scores', 'raw_score')

    op.drop_column('findings', 'evidence_completeness')

    op.drop_index(op.f('ix_review_queue_items_status'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_rank'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_priority_score'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_priority_band'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_finding_id'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_cse_id'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_created_at'), table_name='review_queue_items')
    op.drop_index(op.f('ix_review_queue_items_analysis_run_id'), table_name='review_queue_items')
    op.drop_table('review_queue_items')

    op.drop_index(op.f('ix_maintenance_logs_cse_id'), table_name='maintenance_logs')
    op.drop_index(op.f('ix_maintenance_logs_created_at'), table_name='maintenance_logs')
    op.drop_index(op.f('ix_maintenance_logs_asset_id'), table_name='maintenance_logs')
    op.drop_table('maintenance_logs')
