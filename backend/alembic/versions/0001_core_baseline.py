"""Core baseline: every Core table, the identity schema, roles' grants, triggers and registry rows.

Design doc §6.2–§6.3. Frozen once merged: later changes go in new migrations.
The table-creation section was generated from the models (Alembic autogenerate) and checked by the
drift test; the rest is hand-written.

Revision ID: 0001_core
Revises:
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import Text

revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None

TABLES = (
    'llm_cache',
    'pbs_item',
    'pbs_refresh_log',
    'practice',
    'specialty_module',
    'trial_snapshot',
    'document_type',
    'drug_reference',
    'fact_kind',
    'job_kind',
    'patient',
    'pipeline_run',
    'provider',
    'trial',
    'care_team_member',
    'identity.patient_identity',
    'job',
    'trial_criterion',
    'trial_site',
    'user',
    'document',
    'job_step',
    'next_step',
    'practice_module',
    'redaction_job',
    'verification',
    'cloud_request',
    'extraction',
    'redaction_job_file',
    'extracted_fact',
    'llm_call_log',
    'ocr_page',
    'redaction_log',
    'clinical_note',
    'condition',
    'imaging_study',
    'lab_result',
    'management_plan',
    'redaction_entity',
    'finding',
    'match_run',
    'treatment_course',
    'match_result',
    'medication',
    'report',
    'criterion_evaluation',
    'export',
    'medication_change_log',
)

IMMUTABLE_TABLES = (
    'trial_snapshot',
    'verification',
    'llm_call_log',
    'match_run',
    'match_result',
    'criterion_evaluation',
    'medication_change_log',
)

# The app may hard-delete only here: a cache and the job queue. Everything else is soft-deleted.
APP_DELETABLE_TABLES = ("llm_cache", "job", "job_step")

# Support Views read these; never Patient data or Patient Identity (design doc §6.4).
SUPPORT_READABLE_TABLES = (
    "job",
    "job_step",
    "job_kind",
    "pipeline_run",
    "llm_call_log",
    "cloud_request",
    "pbs_refresh_log",
    "specialty_module",
    "practice_module",
)

CORE_FACT_KINDS = (
    "condition",
    "treatment_course",
    "imaging_study",
    "finding",
    "lab_result",
    "medication",
    "management_plan",
    "clinical_note",
)


def quoted(table: str) -> str:
    schema, _, name = table.rpartition(".")
    return f'{schema}."{name}"' if schema else f'"{name}"'


def upgrade() -> None:
    # Patient Identity lives apart, reachable only through the identity_access role.
    op.execute("CREATE SCHEMA identity")
    op.execute("REVOKE ALL ON SCHEMA identity FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA identity TO identity_access")
    # Every table created by vigil_owner from here on: the app may read, insert and update, never delete.
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO vigil_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA identity"
        " GRANT SELECT, INSERT, UPDATE ON TABLES TO identity_access"
    )

    op.create_table('llm_cache',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('cache_key', sa.Text(), nullable=False),
    sa.Column('response', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_llm_cache_soft_delete')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_llm_cache')),
    sa.UniqueConstraint('cache_key', name=op.f('uq_llm_cache_cache_key'))
    )
    op.create_index(op.f('ix_llm_cache_deleted_by_user_id'), 'llm_cache', ['deleted_by_user_id'], unique=False)
    op.create_table('pbs_item',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('item_code', sa.Text(), nullable=False),
    sa.Column('drug_name', sa.Text(), nullable=False),
    sa.Column('brand_names', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('restriction_level', sa.Text(), nullable=False),
    sa.Column('indications', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('max_quantity', sa.Integer(), nullable=True),
    sa.Column('repeats', sa.Integer(), nullable=True),
    sa.Column('patient_copay_general', sa.Numeric(), nullable=True),
    sa.Column('patient_copay_concessional', sa.Numeric(), nullable=True),
    sa.Column('schedule_date', sa.Date(), nullable=False),
    sa.Column('raw_data', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("restriction_level IN ('unrestricted', 'restricted', 'authority_required', 'authority_required_streamlined')", name=op.f('ck_pbs_item_restriction_level_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_pbs_item_soft_delete')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pbs_item')),
    sa.UniqueConstraint('item_code', 'schedule_date', name=op.f('uq_pbs_item_item_code_schedule_date'))
    )
    op.create_index(op.f('ix_pbs_item_deleted_by_user_id'), 'pbs_item', ['deleted_by_user_id'], unique=False)
    op.create_table('pbs_refresh_log',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('schedule_date', sa.Date(), nullable=True),
    sa.Column('refreshed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('item_count', sa.Integer(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('succeeded', 'partial', 'failed')", name=op.f('ck_pbs_refresh_log_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_pbs_refresh_log_soft_delete')),
    sa.CheckConstraint('item_count IS NULL OR item_count >= 0', name=op.f('ck_pbs_refresh_log_item_count')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pbs_refresh_log'))
    )
    op.create_index(op.f('ix_pbs_refresh_log_deleted_by_user_id'), 'pbs_refresh_log', ['deleted_by_user_id'], unique=False)
    op.create_table('practice',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('phone', sa.Text(), nullable=True),
    sa.Column('fax', sa.Text(), nullable=True),
    sa.Column('email', sa.Text(), nullable=True),
    sa.Column('abn', sa.Text(), nullable=True),
    sa.Column('lat', sa.Numeric(), nullable=True),
    sa.Column('lng', sa.Numeric(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_practice_soft_delete')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_practice'))
    )
    op.create_index(op.f('ix_practice_deleted_by_user_id'), 'practice', ['deleted_by_user_id'], unique=False)
    op.create_table('specialty_module',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('version', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_specialty_module_soft_delete')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_specialty_module')),
    sa.UniqueConstraint('key', name=op.f('uq_specialty_module_key'))
    )
    op.create_index(op.f('ix_specialty_module_deleted_by_user_id'), 'specialty_module', ['deleted_by_user_id'], unique=False)
    op.create_table('trial_snapshot',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('registry', sa.Text(), nullable=False),
    sa.Column('query_params', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('record_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("registry IN ('CTGOV', 'ANZCTR')", name=op.f('ck_trial_snapshot_registry_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_trial_snapshot_soft_delete')),
    sa.CheckConstraint('record_count >= 0', name=op.f('ck_trial_snapshot_record_count')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trial_snapshot')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_trial_snapshot_deleted_by_user_id'), 'trial_snapshot', ['deleted_by_user_id'], unique=False)
    op.create_table('document_type',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('module_key', sa.Text(), nullable=True),
    sa.Column('json_schema', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('extraction_prompt_ref', sa.Text(), nullable=True),
    sa.Column('version', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_document_type_soft_delete')),
    sa.ForeignKeyConstraint(['module_key'], ['specialty_module.key'], name=op.f('fk_document_type_module_key'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_type')),
    sa.UniqueConstraint('key', name=op.f('uq_document_type_key'))
    )
    op.create_index(op.f('ix_document_type_deleted_by_user_id'), 'document_type', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_document_type_module_key'), 'document_type', ['module_key'], unique=False)
    op.create_table('drug_reference',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('generic_name', sa.Text(), nullable=False),
    sa.Column('brand_names', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('drug_class', sa.Text(), nullable=True),
    sa.Column('atc_code', sa.Text(), nullable=True),
    sa.Column('is_cancer_drug', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('pbs_item_id', sa.UUID(), nullable=True),
    sa.Column('common_doses', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('common_routes', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_drug_reference_soft_delete')),
    sa.ForeignKeyConstraint(['pbs_item_id'], ['pbs_item.id'], name=op.f('fk_drug_reference_pbs_item_id'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_drug_reference')),
    sa.UniqueConstraint('generic_name', name=op.f('uq_drug_reference_generic_name'))
    )
    op.create_index(op.f('ix_drug_reference_deleted_by_user_id'), 'drug_reference', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_drug_reference_pbs_item_id'), 'drug_reference', ['pbs_item_id'], unique=False)
    op.create_table('fact_kind',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('module_key', sa.Text(), nullable=True),
    sa.Column('record_table', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_fact_kind_soft_delete')),
    sa.ForeignKeyConstraint(['module_key'], ['specialty_module.key'], name=op.f('fk_fact_kind_module_key'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fact_kind')),
    sa.UniqueConstraint('key', name=op.f('uq_fact_kind_key'))
    )
    op.create_index(op.f('ix_fact_kind_deleted_by_user_id'), 'fact_kind', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_fact_kind_module_key'), 'fact_kind', ['module_key'], unique=False)
    op.create_table('job_kind',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('module_key', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_job_kind_soft_delete')),
    sa.ForeignKeyConstraint(['module_key'], ['specialty_module.key'], name=op.f('fk_job_kind_module_key'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_kind')),
    sa.UniqueConstraint('key', name=op.f('uq_job_kind_key'))
    )
    op.create_index(op.f('ix_job_kind_deleted_by_user_id'), 'job_kind', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_job_kind_module_key'), 'job_kind', ['module_key'], unique=False)
    op.create_table('patient',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('pseudonym', sa.Text(), nullable=False),
    sa.Column('sex', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_patient_soft_delete')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_patient_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patient')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_patient_id_practice_id')),
    sa.UniqueConstraint('pseudonym', name=op.f('uq_patient_pseudonym'))
    )
    op.create_index(op.f('ix_patient_deleted_by_user_id'), 'patient', ['deleted_by_user_id'], unique=False)
    op.create_index('ix_patient_not_deleted', 'patient', ['id'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index(op.f('ix_patient_practice_id'), 'patient', ['practice_id'], unique=False)
    op.create_table('pipeline_run',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=True),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'queued'"), nullable=False),
    sa.Column('inputs', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('versions', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("kind IN ('ingest', 'extract', 'match', 'report', 'pbs_refresh', 'trial_refresh', 'eviq_refresh', 'ocr', 'mask', 'redaction_job', 'reference_set_eval')", name=op.f('ck_pipeline_run_kind_allowed')),
    sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name=op.f('ck_pipeline_run_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_pipeline_run_soft_delete')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_pipeline_run_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pipeline_run'))
    )
    op.create_index(op.f('ix_pipeline_run_deleted_by_user_id'), 'pipeline_run', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_pipeline_run_practice_id'), 'pipeline_run', ['practice_id'], unique=False)
    op.create_table('provider',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('first_name', sa.Text(), nullable=False),
    sa.Column('last_name', sa.Text(), nullable=False),
    sa.Column('provider_number', sa.Text(), nullable=True),
    sa.Column('specialty', sa.Text(), nullable=False),
    sa.Column('is_internal', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('organisation', sa.Text(), nullable=True),
    sa.Column('phone', sa.Text(), nullable=True),
    sa.Column('email', sa.Text(), nullable=True),
    sa.Column('fax', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("specialty IN ('medical_oncology', 'radiation_oncology', 'surgery', 'general_practice', 'haematology', 'pathology', 'radiology', 'other')", name=op.f('ck_provider_specialty_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_provider_soft_delete')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_provider_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_provider_id_practice_id'))
    )
    op.create_index(op.f('ix_provider_deleted_by_user_id'), 'provider', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_provider_practice_id'), 'provider', ['practice_id'], unique=False)
    op.create_index('uq_provider_practice_id_provider_number', 'provider', ['practice_id', 'provider_number'], unique=True, postgresql_where=sa.text('provider_number IS NOT NULL'))
    op.create_table('trial',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('registry', sa.Text(), nullable=False),
    sa.Column('external_id', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('phase', sa.Text(), nullable=True),
    sa.Column('overall_status', sa.Text(), nullable=True),
    sa.Column('sponsor', sa.Text(), nullable=True),
    sa.Column('conditions', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('interventions', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('snapshot_id', sa.UUID(), nullable=True),
    sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("registry IN ('CTGOV', 'ANZCTR')", name=op.f('ck_trial_registry_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_trial_soft_delete')),
    sa.ForeignKeyConstraint(['snapshot_id'], ['trial_snapshot.id'], name=op.f('fk_trial_snapshot_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trial')),
    sa.UniqueConstraint('registry', 'external_id', name=op.f('uq_trial_registry_external_id'))
    )
    op.create_index('ix_trial_conditions', 'trial', ['conditions'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_trial_deleted_by_user_id'), 'trial', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_trial_snapshot_id'), 'trial', ['snapshot_id'], unique=False)
    op.create_table('care_team_member',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('provider_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("role IN ('treating_oncologist', 'referring_gp', 'referring_specialist', 'surgeon', 'radiation_oncologist', 'trial_site_contact')", name=op.f('ck_care_team_member_role_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_care_team_member_soft_delete')),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_care_team_member_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_care_team_member_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_care_team_member_provider_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_care_team_member')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_care_team_member_id_practice_id'))
    )
    op.create_index(op.f('ix_care_team_member_deleted_by_user_id'), 'care_team_member', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_care_team_member_patient_id'), 'care_team_member', ['patient_id'], unique=False)
    op.create_index(op.f('ix_care_team_member_practice_id'), 'care_team_member', ['practice_id'], unique=False)
    op.create_index(op.f('ix_care_team_member_provider_id'), 'care_team_member', ['provider_id'], unique=False)
    op.create_table('patient_identity',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('given_name', sa.Text(), nullable=False),
    sa.Column('family_name', sa.Text(), nullable=False),
    sa.Column('dob', sa.Date(), nullable=True),
    sa.Column('medicare_number_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('medicare_irn', sa.Text(), nullable=True),
    sa.Column('ihi_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('mrn', sa.Text(), nullable=True),
    sa.Column('address_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('phone_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('mobile_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('email_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('next_of_kin_name', sa.Text(), nullable=True),
    sa.Column('next_of_kin_phone_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_patient_identity_soft_delete')),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_patient_identity_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_patient_identity_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_identity')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_patient_identity_id_practice_id')),
    sa.UniqueConstraint('patient_id', name=op.f('uq_patient_identity_patient_id')),
    schema='identity'
    )
    op.create_index(op.f('ix_patient_identity_deleted_by_user_id'), 'patient_identity', ['deleted_by_user_id'], unique=False, schema='identity')
    op.create_index(op.f('ix_patient_identity_practice_id'), 'patient_identity', ['practice_id'], unique=False, schema='identity')
    op.create_table('job',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=True),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'queued'"), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('priority', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('max_attempts', sa.Integer(), server_default=sa.text('3'), nullable=False),
    sa.Column('run_after', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_by', sa.Text(), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('pipeline_run_id', sa.UUID(), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name=op.f('ck_job_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_job_soft_delete')),
    sa.CheckConstraint('attempts >= 0 AND attempts <= max_attempts', name=op.f('ck_job_attempts')),
    sa.CheckConstraint('max_attempts >= 1', name=op.f('ck_job_max_attempts')),
    sa.ForeignKeyConstraint(['kind'], ['job_kind.key'], name=op.f('fk_job_kind'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_run.id'], name=op.f('fk_job_pipeline_run_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_job_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job'))
    )
    op.create_index('ix_job_claim', 'job', ['status', 'run_after', 'priority'], unique=False)
    op.create_index(op.f('ix_job_deleted_by_user_id'), 'job', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_job_kind'), 'job', ['kind'], unique=False)
    op.create_index(op.f('ix_job_pipeline_run_id'), 'job', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_job_practice_id'), 'job', ['practice_id'], unique=False)
    op.create_table('trial_criterion',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('trial_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('structured', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('attribute', sa.Text(), nullable=True),
    sa.Column('category', sa.Text(), nullable=True),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('parser_version', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("kind IN ('inclusion', 'exclusion')", name=op.f('ck_trial_criterion_kind_allowed')),
    sa.CheckConstraint("scope IN ('target_condition', 'whole_person')", name=op.f('ck_trial_criterion_scope_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_trial_criterion_soft_delete')),
    sa.ForeignKeyConstraint(['trial_id'], ['trial.id'], name=op.f('fk_trial_criterion_trial_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trial_criterion'))
    )
    op.create_index(op.f('ix_trial_criterion_deleted_by_user_id'), 'trial_criterion', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_trial_criterion_trial_id'), 'trial_criterion', ['trial_id'], unique=False)
    op.create_table('trial_site',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('trial_id', sa.UUID(), nullable=False),
    sa.Column('facility', sa.Text(), nullable=True),
    sa.Column('city', sa.Text(), nullable=True),
    sa.Column('state', sa.Text(), nullable=True),
    sa.Column('country', sa.Text(), nullable=True),
    sa.Column('site_status', sa.Text(), nullable=True),
    sa.Column('lat', sa.Numeric(), nullable=True),
    sa.Column('lng', sa.Numeric(), nullable=True),
    sa.Column('travel_min', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_trial_site_soft_delete')),
    sa.ForeignKeyConstraint(['trial_id'], ['trial.id'], name=op.f('fk_trial_site_trial_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trial_site'))
    )
    op.create_index('ix_trial_site_country_city', 'trial_site', ['country', 'city'], unique=False)
    op.create_index(op.f('ix_trial_site_deleted_by_user_id'), 'trial_site', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_trial_site_trial_id'), 'trial_site', ['trial_id'], unique=False)
    op.create_table('user',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('username', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('totp_secret_encrypted', postgresql.BYTEA(), nullable=True),
    sa.Column('totp_enrolled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('job_title', sa.Text(), nullable=False),
    sa.Column('provider_id', sa.UUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("job_title IN ('clinician', 'trial_coordinator', 'secretary', 'developer_admin')", name=op.f('ck_user_job_title_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_user_soft_delete')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_user_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_user_provider_id_practice_id'), ondelete='SET NULL (provider_id)'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_user_id_practice_id')),
    sa.UniqueConstraint('practice_id', 'username', name=op.f('uq_user_practice_id_username'))
    )
    op.create_index(op.f('ix_user_deleted_by_user_id'), 'user', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_user_practice_id'), 'user', ['practice_id'], unique=False)
    op.create_index(op.f('ix_user_provider_id'), 'user', ['provider_id'], unique=False)
    op.create_table('document',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('document_type_id', sa.UUID(), nullable=True),
    sa.Column('original_uri', sa.Text(), nullable=False),
    sa.Column('original_sha256', sa.Text(), nullable=False),
    sa.Column('working_copy_uri', sa.Text(), nullable=True),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column('doc_date', sa.Date(), nullable=True),
    sa.Column('uploaded_by_user_id', sa.UUID(), nullable=False),
    sa.Column('input_method', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'uploaded'"), nullable=False),
    sa.Column('hold_reason', sa.Text(), nullable=True),
    sa.Column('held_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("(status = 'held') = (hold_reason IS NOT NULL)", name=op.f('ck_document_hold_reason_when_held')),
    sa.CheckConstraint("hold_reason IN ('unreadable', 'unknown_type', 'pii_uncertain', 'user_held')", name=op.f('ck_document_hold_reason_allowed')),
    sa.CheckConstraint("input_method IN ('native_pdf', 'scan', 'photo', 'fax')", name=op.f('ck_document_input_method_allowed')),
    sa.CheckConstraint("status IN ('uploaded', 'ocr', 'masking', 'redaction_review', 'classifying', 'extracting', 'in_review', 'complete', 'held', 'failed')", name=op.f('ck_document_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_document_soft_delete')),
    sa.CheckConstraint('page_count IS NULL OR page_count >= 1', name=op.f('ck_document_page_count_positive')),
    sa.ForeignKeyConstraint(['document_type_id'], ['document_type.id'], name=op.f('fk_document_document_type_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['held_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_document_held_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_document_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_document_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploaded_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_document_uploaded_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_document_id_practice_id')),
    sa.UniqueConstraint('patient_id', 'original_sha256', name=op.f('uq_document_patient_id_original_sha256'))
    )
    op.create_index(op.f('ix_document_deleted_by_user_id'), 'document', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_document_document_type_id'), 'document', ['document_type_id'], unique=False)
    op.create_index('ix_document_held', 'document', ['patient_id'], unique=False, postgresql_where=sa.text("status = 'held'"))
    op.create_index(op.f('ix_document_held_by_user_id'), 'document', ['held_by_user_id'], unique=False)
    op.create_index(op.f('ix_document_patient_id'), 'document', ['patient_id'], unique=False)
    op.create_index('ix_document_patient_id_doc_date', 'document', ['patient_id', sa.literal_column('doc_date DESC')], unique=False)
    op.create_index(op.f('ix_document_practice_id'), 'document', ['practice_id'], unique=False)
    op.create_index(op.f('ix_document_uploaded_by_user_id'), 'document', ['uploaded_by_user_id'], unique=False)
    op.create_table('job_step',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('job_id', sa.UUID(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('output', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('pending', 'running', 'succeeded', 'failed', 'skipped')", name=op.f('ck_job_step_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_job_step_soft_delete')),
    sa.CheckConstraint('sequence >= 0', name=op.f('ck_job_step_sequence')),
    sa.ForeignKeyConstraint(['job_id'], ['job.id'], name=op.f('fk_job_step_job_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_step')),
    sa.UniqueConstraint('job_id', 'sequence', name=op.f('uq_job_step_job_id_sequence'))
    )
    op.create_index(op.f('ix_job_step_deleted_by_user_id'), 'job_step', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_job_step_job_id'), 'job_step', ['job_id'], unique=False)
    op.create_table('next_step',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=False),
    sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('done_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("kind IN ('rescan', 'mdt', 'trial_window', 'review', 'other')", name=op.f('ck_next_step_kind_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_next_step_soft_delete')),
    sa.CheckConstraint('(done_at IS NULL) = (done_by_user_id IS NULL)', name=op.f('ck_next_step_done_together')),
    sa.ForeignKeyConstraint(['created_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_next_step_created_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['done_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_next_step_done_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_next_step_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_next_step_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_next_step')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_next_step_id_practice_id'))
    )
    op.create_index(op.f('ix_next_step_created_by_user_id'), 'next_step', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_next_step_deleted_by_user_id'), 'next_step', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_next_step_done_by_user_id'), 'next_step', ['done_by_user_id'], unique=False)
    op.create_index(op.f('ix_next_step_patient_id'), 'next_step', ['patient_id'], unique=False)
    op.create_index(op.f('ix_next_step_practice_id'), 'next_step', ['practice_id'], unique=False)
    op.create_table('practice_module',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('module_key', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('changed_by_user_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_practice_module_soft_delete')),
    sa.ForeignKeyConstraint(['changed_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_practice_module_changed_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['module_key'], ['specialty_module.key'], name=op.f('fk_practice_module_module_key'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_practice_module_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_practice_module')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_practice_module_id_practice_id')),
    sa.UniqueConstraint('practice_id', 'module_key', name=op.f('uq_practice_module_practice_id_module_key'))
    )
    op.create_index(op.f('ix_practice_module_changed_by_user_id'), 'practice_module', ['changed_by_user_id'], unique=False)
    op.create_index(op.f('ix_practice_module_deleted_by_user_id'), 'practice_module', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_practice_module_module_key'), 'practice_module', ['module_key'], unique=False)
    op.create_index(op.f('ix_practice_module_practice_id'), 'practice_module', ['practice_id'], unique=False)
    op.create_table('redaction_job',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=False),
    sa.Column('purpose', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("purpose IN ('trial_portal', 'referral', 'other')", name=op.f('ck_redaction_job_purpose_allowed')),
    sa.CheckConstraint("status IN ('draft', 'processing', 'in_review', 'complete', 'failed')", name=op.f('ck_redaction_job_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_redaction_job_soft_delete')),
    sa.ForeignKeyConstraint(['created_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_redaction_job_created_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_redaction_job_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_redaction_job_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_redaction_job')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_redaction_job_id_practice_id'))
    )
    op.create_index(op.f('ix_redaction_job_created_by_user_id'), 'redaction_job', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_redaction_job_deleted_by_user_id'), 'redaction_job', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_redaction_job_patient_id'), 'redaction_job', ['patient_id'], unique=False)
    op.create_index(op.f('ix_redaction_job_practice_id'), 'redaction_job', ['practice_id'], unique=False)
    op.create_table('verification',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('subject_table', sa.Text(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('job_title_at_time', sa.Text(), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('before', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('after', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('reauthenticated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("action IN ('accept', 'edit', 'reject', 'override', 'attribute', 'sign_off_export', 'delete', 'move', 'hold', 'activate_module', 'deactivate_module')", name=op.f('ck_verification_action_allowed')),
    sa.CheckConstraint("job_title_at_time IN ('clinician', 'trial_coordinator', 'secretary', 'developer_admin')", name=op.f('ck_verification_job_title_at_time_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_verification_soft_delete')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_verification_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_verification_user_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_verification')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_verification_id_practice_id')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_verification_deleted_by_user_id'), 'verification', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_verification_practice_id'), 'verification', ['practice_id'], unique=False)
    op.create_index('ix_verification_subject', 'verification', ['subject_table', 'subject_id'], unique=False)
    op.create_index(op.f('ix_verification_user_id'), 'verification', ['user_id'], unique=False)
    op.create_table('cloud_request',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=True),
    sa.Column('request_id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('page_numbers', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('purpose', sa.Text(), nullable=False),
    sa.Column('payload_kind', sa.Text(), nullable=False),
    sa.Column('payload_sha256', sa.Text(), nullable=False),
    sa.Column('initiated_by_user_id', sa.UUID(), nullable=True),
    sa.Column('model_id', sa.Text(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("(payload_kind = 'public_text' AND document_id IS NULL) OR (payload_kind <> 'public_text' AND practice_id IS NOT NULL AND document_id IS NOT NULL)", name=op.f('ck_cloud_request_patient_payload_has_document')),
    sa.CheckConstraint("payload_kind IN ('masked_image', 'pseudonymised_text', 'public_text')", name=op.f('ck_cloud_request_payload_kind_allowed')),
    sa.CheckConstraint("purpose IN ('vlm_read', 'classify', 'extract', 'adjudicate', 'parse_criteria')", name=op.f('ck_cloud_request_purpose_allowed')),
    sa.CheckConstraint("status IN ('pending', 'sent', 'received', 'failed')", name=op.f('ck_cloud_request_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_cloud_request_soft_delete')),
    sa.ForeignKeyConstraint(['document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_cloud_request_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['document_id'], ['document.id'], name=op.f('fk_cloud_request_document_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['initiated_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_cloud_request_initiated_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['initiated_by_user_id'], ['user.id'], name=op.f('fk_cloud_request_initiated_by_user_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_cloud_request_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cloud_request')),
    sa.UniqueConstraint('request_id', name=op.f('uq_cloud_request_request_id'))
    )
    op.create_index(op.f('ix_cloud_request_deleted_by_user_id'), 'cloud_request', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_cloud_request_document_id'), 'cloud_request', ['document_id'], unique=False)
    op.create_index(op.f('ix_cloud_request_initiated_by_user_id'), 'cloud_request', ['initiated_by_user_id'], unique=False)
    op.create_index(op.f('ix_cloud_request_practice_id'), 'cloud_request', ['practice_id'], unique=False)
    op.create_table('extraction',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('document_type_id', sa.UUID(), nullable=False),
    sa.Column('pipeline_run_id', sa.UUID(), nullable=True),
    sa.Column('reader', sa.Text(), nullable=False),
    sa.Column('model_id', sa.Text(), nullable=True),
    sa.Column('prompt_version', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("reader IN ('text_layer', 'classic_ocr', 'local_vlm', 'cloud_vlm')", name=op.f('ck_extraction_reader_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_extraction_soft_delete')),
    sa.ForeignKeyConstraint(['document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_extraction_document_id_practice_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['document_type_id'], ['document_type.id'], name=op.f('fk_extraction_document_type_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_run.id'], name=op.f('fk_extraction_pipeline_run_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_extraction_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extraction')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_extraction_id_practice_id'))
    )
    op.create_index(op.f('ix_extraction_deleted_by_user_id'), 'extraction', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_extraction_document_id'), 'extraction', ['document_id'], unique=False)
    op.create_index(op.f('ix_extraction_document_type_id'), 'extraction', ['document_type_id'], unique=False)
    op.create_index(op.f('ix_extraction_pipeline_run_id'), 'extraction', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_extraction_practice_id'), 'extraction', ['practice_id'], unique=False)
    op.create_table('redaction_job_file',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('redaction_job_id', sa.UUID(), nullable=False),
    sa.Column('original_uri', sa.Text(), nullable=False),
    sa.Column('original_sha256', sa.Text(), nullable=False),
    sa.Column('redacted_uri', sa.Text(), nullable=True),
    sa.Column('redacted_sha256', sa.Text(), nullable=True),
    sa.Column('leak_check_passed', sa.Boolean(), nullable=True),
    sa.Column('leak_check_report', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_redaction_job_file_soft_delete')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_redaction_job_file_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['redaction_job_id', 'practice_id'], ['redaction_job.id', 'redaction_job.practice_id'], name=op.f('fk_redaction_job_file_redaction_job_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_redaction_job_file')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_redaction_job_file_id_practice_id'))
    )
    op.create_index(op.f('ix_redaction_job_file_deleted_by_user_id'), 'redaction_job_file', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_redaction_job_file_practice_id'), 'redaction_job_file', ['practice_id'], unique=False)
    op.create_index(op.f('ix_redaction_job_file_redaction_job_id'), 'redaction_job_file', ['redaction_job_id'], unique=False)
    op.create_table('extracted_fact',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('extraction_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('fact_kind', sa.Text(), nullable=False),
    sa.Column('module_key', sa.Text(), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('source_locations', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('confidence', sa.Numeric(), nullable=False),
    sa.Column('confidence_band', sa.Text(), nullable=False),
    sa.Column('numeric_crosscheck', sa.Text(), server_default=sa.text("'not_applicable'"), nullable=False),
    sa.Column('required_job_title', sa.Text(), nullable=False),
    sa.Column('review_status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('accepted_record_table', sa.Text(), nullable=True),
    sa.Column('accepted_record_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("confidence_band IN ('high', 'medium', 'low')", name=op.f('ck_extracted_fact_confidence_band_allowed')),
    sa.CheckConstraint("numeric_crosscheck IN ('agree', 'disagree', 'not_applicable')", name=op.f('ck_extracted_fact_numeric_crosscheck_allowed')),
    sa.CheckConstraint("required_job_title IN ('clinician', 'trial_coordinator', 'secretary')", name=op.f('ck_extracted_fact_required_job_title_allowed')),
    sa.CheckConstraint("review_status IN ('pending', 'accepted', 'edited', 'rejected', 'withdrawn')", name=op.f('ck_extracted_fact_review_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_extracted_fact_soft_delete')),
    sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name=op.f('ck_extracted_fact_confidence_range')),
    sa.ForeignKeyConstraint(['extraction_id', 'practice_id'], ['extraction.id', 'extraction.practice_id'], name=op.f('fk_extracted_fact_extraction_id_practice_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['fact_kind'], ['fact_kind.key'], name=op.f('fk_extracted_fact_fact_kind'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['module_key'], ['specialty_module.key'], name=op.f('fk_extracted_fact_module_key'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_extracted_fact_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_extracted_fact_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extracted_fact')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_extracted_fact_id_practice_id'))
    )
    op.create_index(op.f('ix_extracted_fact_deleted_by_user_id'), 'extracted_fact', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_extracted_fact_extraction_id'), 'extracted_fact', ['extraction_id'], unique=False)
    op.create_index(op.f('ix_extracted_fact_fact_kind'), 'extracted_fact', ['fact_kind'], unique=False)
    op.create_index(op.f('ix_extracted_fact_module_key'), 'extracted_fact', ['module_key'], unique=False)
    op.create_index(op.f('ix_extracted_fact_patient_id'), 'extracted_fact', ['patient_id'], unique=False)
    op.create_index(op.f('ix_extracted_fact_practice_id'), 'extracted_fact', ['practice_id'], unique=False)
    op.create_index('ix_extracted_fact_review_queue', 'extracted_fact', ['review_status', 'required_job_title'], unique=False)
    op.create_table('llm_call_log',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=True),
    sa.Column('pipeline_step', sa.Text(), nullable=False),
    sa.Column('endpoint', sa.Text(), nullable=False),
    sa.Column('cloud_request_id', sa.UUID(), nullable=True),
    sa.Column('model_id', sa.Text(), nullable=False),
    sa.Column('prompt_version', sa.Text(), nullable=True),
    sa.Column('tokens_in', sa.Integer(), nullable=True),
    sa.Column('tokens_out', sa.Integer(), nullable=True),
    sa.Column('cost_aud', sa.Numeric(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('input_hash', sa.Text(), nullable=False),
    sa.Column('cache_hit', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("endpoint IN ('local_vlm', 'cloud')", name=op.f('ck_llm_call_log_endpoint_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_llm_call_log_soft_delete')),
    sa.ForeignKeyConstraint(['cloud_request_id'], ['cloud_request.id'], name=op.f('fk_llm_call_log_cloud_request_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_llm_call_log_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_llm_call_log')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_llm_call_log_cloud_request_id'), 'llm_call_log', ['cloud_request_id'], unique=False)
    op.create_index(op.f('ix_llm_call_log_deleted_by_user_id'), 'llm_call_log', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_llm_call_log_practice_id'), 'llm_call_log', ['practice_id'], unique=False)
    op.create_table('ocr_page',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('redaction_job_file_id', sa.UUID(), nullable=True),
    sa.Column('page_number', sa.Integer(), nullable=False),
    sa.Column('engine', sa.Text(), nullable=False),
    sa.Column('engine_version', sa.Text(), nullable=False),
    sa.Column('words', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('mean_confidence', sa.Numeric(), nullable=True),
    sa.Column('rotation_deg', sa.Numeric(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("engine IN ('ppocr_v5', 'doctr')", name=op.f('ck_ocr_page_engine_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_ocr_page_soft_delete')),
    sa.CheckConstraint('num_nonnulls(document_id, redaction_job_file_id) = 1', name=op.f('ck_ocr_page_one_parent')),
    sa.CheckConstraint('page_number >= 1', name=op.f('ck_ocr_page_page_number_positive')),
    sa.ForeignKeyConstraint(['document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_ocr_page_document_id_practice_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_ocr_page_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['redaction_job_file_id', 'practice_id'], ['redaction_job_file.id', 'redaction_job_file.practice_id'], name=op.f('fk_ocr_page_redaction_job_file_id_practice_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ocr_page')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_ocr_page_id_practice_id'))
    )
    op.create_index(op.f('ix_ocr_page_deleted_by_user_id'), 'ocr_page', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_ocr_page_document_id'), 'ocr_page', ['document_id'], unique=False)
    op.create_index(op.f('ix_ocr_page_practice_id'), 'ocr_page', ['practice_id'], unique=False)
    op.create_index(op.f('ix_ocr_page_redaction_job_file_id'), 'ocr_page', ['redaction_job_file_id'], unique=False)
    op.create_table('redaction_log',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('redaction_job_file_id', sa.UUID(), nullable=True),
    sa.Column('pipeline_run_id', sa.UUID(), nullable=True),
    sa.Column('entity_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('min_confidence', sa.Numeric(), nullable=True),
    sa.Column('required_manual_review', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('leak_check_passed', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_redaction_log_soft_delete')),
    sa.CheckConstraint('entity_count >= 0', name=op.f('ck_redaction_log_entity_count')),
    sa.CheckConstraint('num_nonnulls(document_id, redaction_job_file_id) = 1', name=op.f('ck_redaction_log_one_parent')),
    sa.ForeignKeyConstraint(['document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_redaction_log_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_run.id'], name=op.f('fk_redaction_log_pipeline_run_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_redaction_log_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['redaction_job_file_id', 'practice_id'], ['redaction_job_file.id', 'redaction_job_file.practice_id'], name=op.f('fk_redaction_log_redaction_job_file_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewed_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_redaction_log_reviewed_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_redaction_log')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_redaction_log_id_practice_id'))
    )
    op.create_index(op.f('ix_redaction_log_deleted_by_user_id'), 'redaction_log', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_redaction_log_document_id'), 'redaction_log', ['document_id'], unique=False)
    op.create_index(op.f('ix_redaction_log_pipeline_run_id'), 'redaction_log', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_redaction_log_practice_id'), 'redaction_log', ['practice_id'], unique=False)
    op.create_index(op.f('ix_redaction_log_redaction_job_file_id'), 'redaction_log', ['redaction_job_file_id'], unique=False)
    op.create_index(op.f('ix_redaction_log_reviewed_by_user_id'), 'redaction_log', ['reviewed_by_user_id'], unique=False)
    op.create_table('clinical_note',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('note_type', sa.Text(), nullable=False),
    sa.Column('author_provider_id', sa.UUID(), nullable=True),
    sa.Column('recipient_provider_id', sa.UUID(), nullable=True),
    sa.Column('note_date', sa.Date(), nullable=True),
    sa.Column('content_summary', sa.Text(), nullable=True),
    sa.Column('key_points', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("note_type IN ('clinical_note', 'letter_to_referrer', 'discharge_summary')", name=op.f('ck_clinical_note_note_type_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_clinical_note_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_clinical_note_provenance')),
    sa.ForeignKeyConstraint(['author_provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_clinical_note_author_provider_id_practice_id'), ondelete='SET NULL (author_provider_id)'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_clinical_note_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_clinical_note_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_clinical_note_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recipient_provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_clinical_note_recipient_provider_id_practice_id'), ondelete='SET NULL (recipient_provider_id)'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_clinical_note_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_clinical_note_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clinical_note')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_clinical_note_id_practice_id'))
    )
    op.create_index(op.f('ix_clinical_note_author_provider_id'), 'clinical_note', ['author_provider_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_deleted_by_user_id'), 'clinical_note', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_entered_by_user_id'), 'clinical_note', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_patient_id'), 'clinical_note', ['patient_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_practice_id'), 'clinical_note', ['practice_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_recipient_provider_id'), 'clinical_note', ['recipient_provider_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_source_document_id'), 'clinical_note', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_clinical_note_source_fact_id'), 'clinical_note', ['source_fact_id'], unique=False)
    op.create_table('condition',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('code_system', sa.Text(), nullable=True),
    sa.Column('code', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('onset_date', sa.Date(), nullable=True),
    sa.Column('extended_by_module', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('active', 'resolved')", name=op.f('ck_condition_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_condition_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_condition_provenance')),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_condition_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['extended_by_module'], ['specialty_module.key'], name=op.f('fk_condition_extended_by_module'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_condition_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_condition_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_condition_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_condition_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_condition')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_condition_id_practice_id'))
    )
    op.create_index(op.f('ix_condition_deleted_by_user_id'), 'condition', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_condition_entered_by_user_id'), 'condition', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_condition_extended_by_module'), 'condition', ['extended_by_module'], unique=False)
    op.create_index(op.f('ix_condition_patient_id'), 'condition', ['patient_id'], unique=False)
    op.create_index('ix_condition_patient_id_status', 'condition', ['patient_id', 'status'], unique=False)
    op.create_index(op.f('ix_condition_practice_id'), 'condition', ['practice_id'], unique=False)
    op.create_index(op.f('ix_condition_source_document_id'), 'condition', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_condition_source_fact_id'), 'condition', ['source_fact_id'], unique=False)
    op.create_table('imaging_study',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('modality', sa.Text(), nullable=False),
    sa.Column('body_region', sa.Text(), nullable=True),
    sa.Column('study_date', sa.Date(), nullable=False),
    sa.Column('impression', sa.Text(), nullable=True),
    sa.Column('comparison_date', sa.Date(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_imaging_study_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_imaging_study_provenance')),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_imaging_study_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_imaging_study_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_imaging_study_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_imaging_study_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_imaging_study_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_imaging_study')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_imaging_study_id_practice_id'))
    )
    op.create_index(op.f('ix_imaging_study_deleted_by_user_id'), 'imaging_study', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_imaging_study_entered_by_user_id'), 'imaging_study', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_imaging_study_patient_id'), 'imaging_study', ['patient_id'], unique=False)
    op.create_index('ix_imaging_study_patient_modality_date', 'imaging_study', ['patient_id', 'modality', sa.literal_column('study_date DESC')], unique=False)
    op.create_index(op.f('ix_imaging_study_practice_id'), 'imaging_study', ['practice_id'], unique=False)
    op.create_index(op.f('ix_imaging_study_source_document_id'), 'imaging_study', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_imaging_study_source_fact_id'), 'imaging_study', ['source_fact_id'], unique=False)
    op.create_table('lab_result',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('analyte', sa.Text(), nullable=False),
    sa.Column('value', sa.Numeric(), nullable=True),
    sa.Column('value_text', sa.Text(), nullable=True),
    sa.Column('unit', sa.Text(), nullable=True),
    sa.Column('ref_low', sa.Numeric(), nullable=True),
    sa.Column('ref_high', sa.Numeric(), nullable=True),
    sa.Column('flag', sa.Text(), nullable=True),
    sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('panel', sa.Text(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("flag IN ('low', 'normal', 'high', 'critical')", name=op.f('ck_lab_result_flag_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_lab_result_soft_delete')),
    sa.CheckConstraint('num_nonnulls(value, value_text) >= 1', name=op.f('ck_lab_result_has_value')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_lab_result_provenance')),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_lab_result_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_lab_result_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_lab_result_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_lab_result_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_lab_result_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_result')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_lab_result_id_practice_id'))
    )
    op.create_index(op.f('ix_lab_result_deleted_by_user_id'), 'lab_result', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_lab_result_entered_by_user_id'), 'lab_result', ['entered_by_user_id'], unique=False)
    op.create_index('ix_lab_result_patient_analyte_collected', 'lab_result', ['patient_id', 'analyte', sa.literal_column('collected_at DESC')], unique=False)
    op.create_index(op.f('ix_lab_result_patient_id'), 'lab_result', ['patient_id'], unique=False)
    op.create_index(op.f('ix_lab_result_practice_id'), 'lab_result', ['practice_id'], unique=False)
    op.create_index(op.f('ix_lab_result_source_document_id'), 'lab_result', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_lab_result_source_fact_id'), 'lab_result', ['source_fact_id'], unique=False)
    op.create_table('management_plan',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('plan_text', sa.Text(), nullable=False),
    sa.Column('plan_date', sa.Date(), nullable=True),
    sa.Column('authored_by_provider_id', sa.UUID(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_management_plan_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_management_plan_provenance')),
    sa.ForeignKeyConstraint(['authored_by_provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_management_plan_authored_by_provider_id_practice_id'), ondelete='SET NULL (authored_by_provider_id)'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_management_plan_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_management_plan_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_management_plan_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_management_plan_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_management_plan_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_management_plan')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_management_plan_id_practice_id'))
    )
    op.create_index(op.f('ix_management_plan_authored_by_provider_id'), 'management_plan', ['authored_by_provider_id'], unique=False)
    op.create_index(op.f('ix_management_plan_deleted_by_user_id'), 'management_plan', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_management_plan_entered_by_user_id'), 'management_plan', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_management_plan_patient_id'), 'management_plan', ['patient_id'], unique=False)
    op.create_index(op.f('ix_management_plan_practice_id'), 'management_plan', ['practice_id'], unique=False)
    op.create_index(op.f('ix_management_plan_source_document_id'), 'management_plan', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_management_plan_source_fact_id'), 'management_plan', ['source_fact_id'], unique=False)
    op.create_table('redaction_entity',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('redaction_log_id', sa.UUID(), nullable=False),
    sa.Column('entity_type', sa.Text(), nullable=False),
    sa.Column('page_number', sa.Integer(), nullable=False),
    sa.Column('bbox_pt', postgresql.JSONB(astext_type=Text()), nullable=False),
    sa.Column('text_hash', sa.Text(), nullable=False),
    sa.Column('replacement_token', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Numeric(), nullable=True),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("entity_type IN ('NAME', 'DOB', 'MEDICARE', 'IHI', 'DVA', 'MRN', 'ADDRESS', 'PHONE', 'EMAIL', 'PROVIDER_NAME', 'REFERRING_DOCTOR')", name=op.f('ck_redaction_entity_entity_type_allowed')),
    sa.CheckConstraint("origin IN ('auto', 'manual')", name=op.f('ck_redaction_entity_origin_allowed')),
    sa.CheckConstraint("status IN ('active', 'removed_false_positive')", name=op.f('ck_redaction_entity_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_redaction_entity_soft_delete')),
    sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name=op.f('ck_redaction_entity_confidence_range')),
    sa.CheckConstraint('page_number >= 1', name=op.f('ck_redaction_entity_page_number_positive')),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_redaction_entity_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['redaction_log_id', 'practice_id'], ['redaction_log.id', 'redaction_log.practice_id'], name=op.f('fk_redaction_entity_redaction_log_id_practice_id'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_redaction_entity')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_redaction_entity_id_practice_id'))
    )
    op.create_index(op.f('ix_redaction_entity_deleted_by_user_id'), 'redaction_entity', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_redaction_entity_practice_id'), 'redaction_entity', ['practice_id'], unique=False)
    op.create_index(op.f('ix_redaction_entity_redaction_log_id'), 'redaction_entity', ['redaction_log_id'], unique=False)
    op.create_table('finding',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('imaging_study_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('condition_id', sa.UUID(), nullable=True),
    sa.Column('site', sa.Text(), nullable=True),
    sa.Column('laterality', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('size_mm', sa.Numeric(), nullable=True),
    sa.Column('suv_max', sa.Numeric(), nullable=True),
    sa.Column('is_new', sa.Boolean(), nullable=True),
    sa.Column('is_measurable', sa.Boolean(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_finding_soft_delete')),
    sa.CheckConstraint('size_mm IS NULL OR size_mm > 0', name=op.f('ck_finding_size_positive')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_finding_provenance')),
    sa.CheckConstraint('suv_max IS NULL OR suv_max >= 0', name=op.f('ck_finding_suv_non_negative')),
    sa.ForeignKeyConstraint(['condition_id', 'practice_id'], ['condition.id', 'condition.practice_id'], name=op.f('fk_finding_condition_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_finding_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['imaging_study_id', 'practice_id'], ['imaging_study.id', 'imaging_study.practice_id'], name=op.f('fk_finding_imaging_study_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_finding_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_finding_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_finding_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_finding_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_finding')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_finding_id_practice_id'))
    )
    op.create_index(op.f('ix_finding_condition_id'), 'finding', ['condition_id'], unique=False)
    op.create_index(op.f('ix_finding_deleted_by_user_id'), 'finding', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_finding_entered_by_user_id'), 'finding', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_finding_imaging_study_id'), 'finding', ['imaging_study_id'], unique=False)
    op.create_index(op.f('ix_finding_patient_id'), 'finding', ['patient_id'], unique=False)
    op.create_index(op.f('ix_finding_practice_id'), 'finding', ['practice_id'], unique=False)
    op.create_index(op.f('ix_finding_source_document_id'), 'finding', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_finding_source_fact_id'), 'finding', ['source_fact_id'], unique=False)
    op.create_table('match_run',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('target_condition_id', sa.UUID(), nullable=False),
    sa.Column('snapshot_id', sa.UUID(), nullable=False),
    sa.Column('clinical_record_as_of', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ruleset_version', sa.Text(), nullable=False),
    sa.Column('model_version', sa.Text(), nullable=True),
    sa.Column('run_by_user_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_match_run_soft_delete')),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_match_run_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_match_run_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['run_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_match_run_run_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['snapshot_id'], ['trial_snapshot.id'], name=op.f('fk_match_run_snapshot_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['target_condition_id', 'practice_id'], ['condition.id', 'condition.practice_id'], name=op.f('fk_match_run_target_condition_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_match_run')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_match_run_id_practice_id')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_match_run_deleted_by_user_id'), 'match_run', ['deleted_by_user_id'], unique=False)
    op.create_index('ix_match_run_latest', 'match_run', ['patient_id', 'target_condition_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_index(op.f('ix_match_run_patient_id'), 'match_run', ['patient_id'], unique=False)
    op.create_index(op.f('ix_match_run_practice_id'), 'match_run', ['practice_id'], unique=False)
    op.create_index(op.f('ix_match_run_run_by_user_id'), 'match_run', ['run_by_user_id'], unique=False)
    op.create_index(op.f('ix_match_run_snapshot_id'), 'match_run', ['snapshot_id'], unique=False)
    op.create_index(op.f('ix_match_run_target_condition_id'), 'match_run', ['target_condition_id'], unique=False)
    op.create_table('treatment_course',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('condition_id', sa.UUID(), nullable=False),
    sa.Column('modality', sa.Text(), nullable=False),
    sa.Column('intent', sa.Text(), nullable=True),
    sa.Column('regimen_name', sa.Text(), nullable=True),
    sa.Column('regimen_planned', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('reason_stopped', sa.Text(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("intent IN ('curative', 'neoadjuvant', 'adjuvant', 'palliative')", name=op.f('ck_treatment_course_intent_allowed')),
    sa.CheckConstraint("modality = 'systemic' OR (regimen_name IS NULL AND regimen_planned IS NULL)", name=op.f('ck_treatment_course_regimen_systemic_only')),
    sa.CheckConstraint("modality IN ('systemic', 'surgery', 'radiation')", name=op.f('ck_treatment_course_modality_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_treatment_course_soft_delete')),
    sa.CheckConstraint('end_date IS NULL OR end_date >= start_date', name=op.f('ck_treatment_course_dates_ordered')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_treatment_course_provenance')),
    sa.ForeignKeyConstraint(['condition_id', 'practice_id'], ['condition.id', 'condition.practice_id'], name=op.f('fk_treatment_course_condition_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_treatment_course_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_treatment_course_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_treatment_course_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_treatment_course_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_treatment_course')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_treatment_course_id_practice_id'))
    )
    op.create_index(op.f('ix_treatment_course_condition_id'), 'treatment_course', ['condition_id'], unique=False)
    op.create_index('ix_treatment_course_condition_id_start_date', 'treatment_course', ['condition_id', 'start_date'], unique=False)
    op.create_index(op.f('ix_treatment_course_deleted_by_user_id'), 'treatment_course', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_treatment_course_entered_by_user_id'), 'treatment_course', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_treatment_course_practice_id'), 'treatment_course', ['practice_id'], unique=False)
    op.create_index(op.f('ix_treatment_course_source_document_id'), 'treatment_course', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_treatment_course_source_fact_id'), 'treatment_course', ['source_fact_id'], unique=False)
    op.create_table('match_result',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('match_run_id', sa.UUID(), nullable=False),
    sa.Column('trial_id', sa.UUID(), nullable=False),
    sa.Column('match_state', sa.Text(), nullable=False),
    sa.Column('score', sa.Numeric(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("match_state IN ('POTENTIALLY_ELIGIBLE', 'NEEDS_INFORMATION', 'EXCLUDED')", name=op.f('ck_match_result_match_state_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_match_result_soft_delete')),
    sa.ForeignKeyConstraint(['match_run_id', 'practice_id'], ['match_run.id', 'match_run.practice_id'], name=op.f('fk_match_result_match_run_id_practice_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_match_result_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['trial_id'], ['trial.id'], name=op.f('fk_match_result_trial_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_match_result')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_match_result_id_practice_id')),
    sa.UniqueConstraint('match_run_id', 'trial_id', name=op.f('uq_match_result_match_run_id_trial_id')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_match_result_deleted_by_user_id'), 'match_result', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_match_result_match_run_id'), 'match_result', ['match_run_id'], unique=False)
    op.create_index(op.f('ix_match_result_practice_id'), 'match_result', ['practice_id'], unique=False)
    op.create_index(op.f('ix_match_result_trial_id'), 'match_result', ['trial_id'], unique=False)
    op.create_table('medication',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('drug_reference_id', sa.UUID(), nullable=True),
    sa.Column('drug_name_raw', sa.Text(), nullable=False),
    sa.Column('generic_name', sa.Text(), nullable=True),
    sa.Column('brand_name', sa.Text(), nullable=True),
    sa.Column('dose_amount', sa.Numeric(), nullable=True),
    sa.Column('dose_unit', sa.Text(), nullable=True),
    sa.Column('dose_display', sa.Text(), nullable=True),
    sa.Column('frequency', sa.Text(), nullable=True),
    sa.Column('frequency_detail', sa.Text(), nullable=True),
    sa.Column('route', sa.Text(), nullable=True),
    sa.Column('indication', sa.Text(), nullable=True),
    sa.Column('category', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('reason_discontinued', sa.Text(), nullable=True),
    sa.Column('prescribed_by_provider_id', sa.UUID(), nullable=True),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('confidence', sa.Text(), nullable=False),
    sa.Column('treatment_course_id', sa.UUID(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("category IN ('cancer_treatment', 'supportive_care', 'comorbidity_management', 'supplement', 'other')", name=op.f('ck_medication_category_allowed')),
    sa.CheckConstraint("confidence IN ('high', 'medium', 'low')", name=op.f('ck_medication_confidence_allowed')),
    sa.CheckConstraint("frequency IN ('daily', 'twice_daily', 'three_times_daily', 'weekly', 'fortnightly', 'monthly', 'prn', 'stat', 'other')", name=op.f('ck_medication_frequency_allowed')),
    sa.CheckConstraint("route IN ('oral', 'iv', 'subcut', 'im', 'topical', 'inhaled', 'pr', 'other')", name=op.f('ck_medication_route_allowed')),
    sa.CheckConstraint("source IN ('patient_reported', 'document_extracted', 'doctor_entered', 'pharmacy_list')", name=op.f('ck_medication_source_allowed')),
    sa.CheckConstraint("status IN ('active', 'discontinued', 'on_hold', 'completed', 'unknown')", name=op.f('ck_medication_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_medication_soft_delete')),
    sa.CheckConstraint('dose_amount IS NULL OR dose_amount > 0', name=op.f('ck_medication_dose_positive')),
    sa.CheckConstraint('end_date IS NULL OR end_date >= start_date', name=op.f('ck_medication_dates_ordered')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_medication_provenance')),
    sa.ForeignKeyConstraint(['drug_reference_id'], ['drug_reference.id'], name=op.f('fk_medication_drug_reference_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_medication_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_medication_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_medication_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['prescribed_by_provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_medication_prescribed_by_provider_id_practice_id'), ondelete='SET NULL (prescribed_by_provider_id)'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_medication_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_medication_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['treatment_course_id', 'practice_id'], ['treatment_course.id', 'treatment_course.practice_id'], name=op.f('fk_medication_treatment_course_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_medication')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_medication_id_practice_id'))
    )
    op.create_index(op.f('ix_medication_deleted_by_user_id'), 'medication', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_medication_drug_reference_id'), 'medication', ['drug_reference_id'], unique=False)
    op.create_index(op.f('ix_medication_entered_by_user_id'), 'medication', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_medication_patient_id'), 'medication', ['patient_id'], unique=False)
    op.create_index(op.f('ix_medication_practice_id'), 'medication', ['practice_id'], unique=False)
    op.create_index(op.f('ix_medication_prescribed_by_provider_id'), 'medication', ['prescribed_by_provider_id'], unique=False)
    op.create_index(op.f('ix_medication_source_document_id'), 'medication', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_medication_source_fact_id'), 'medication', ['source_fact_id'], unique=False)
    op.create_index(op.f('ix_medication_treatment_course_id'), 'medication', ['treatment_course_id'], unique=False)
    op.create_table('report',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('match_run_id', sa.UUID(), nullable=True),
    sa.Column('report_type', sa.Text(), nullable=False),
    sa.Column('template_version', sa.Text(), nullable=False),
    sa.Column('manifest', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('file_uri', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("report_type IN ('treatment_summary', 'trial_match', 'patient_summary_snapshot', 'combined')", name=op.f('ck_report_report_type_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_report_soft_delete')),
    sa.ForeignKeyConstraint(['match_run_id', 'practice_id'], ['match_run.id', 'match_run.practice_id'], name=op.f('fk_report_match_run_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_report_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_report_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_report')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_report_id_practice_id'))
    )
    op.create_index(op.f('ix_report_deleted_by_user_id'), 'report', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_report_match_run_id'), 'report', ['match_run_id'], unique=False)
    op.create_index(op.f('ix_report_patient_id'), 'report', ['patient_id'], unique=False)
    op.create_index(op.f('ix_report_practice_id'), 'report', ['practice_id'], unique=False)
    op.create_table('criterion_evaluation',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('match_result_id', sa.UUID(), nullable=False),
    sa.Column('trial_criterion_id', sa.UUID(), nullable=False),
    sa.Column('result', sa.Text(), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=True),
    sa.Column('evidence_ref', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("result IN ('MET', 'NOT_MET', 'UNKNOWN')", name=op.f('ck_criterion_evaluation_result_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_criterion_evaluation_soft_delete')),
    sa.ForeignKeyConstraint(['match_result_id', 'practice_id'], ['match_result.id', 'match_result.practice_id'], name=op.f('fk_criterion_evaluation_match_result_id_practice_id'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_criterion_evaluation_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['trial_criterion_id'], ['trial_criterion.id'], name=op.f('fk_criterion_evaluation_trial_criterion_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_criterion_evaluation')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_criterion_evaluation_id_practice_id')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_criterion_evaluation_deleted_by_user_id'), 'criterion_evaluation', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_criterion_evaluation_match_result_id'), 'criterion_evaluation', ['match_result_id'], unique=False)
    op.create_index(op.f('ix_criterion_evaluation_practice_id'), 'criterion_evaluation', ['practice_id'], unique=False)
    op.create_index(op.f('ix_criterion_evaluation_trial_criterion_id'), 'criterion_evaluation', ['trial_criterion_id'], unique=False)
    op.create_table('export',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=True),
    sa.Column('report_id', sa.UUID(), nullable=True),
    sa.Column('redaction_job_id', sa.UUID(), nullable=True),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('recipient_description', sa.Text(), nullable=False),
    sa.Column('recipient_provider_id', sa.UUID(), nullable=True),
    sa.Column('file_uri', sa.Text(), nullable=False),
    sa.Column('file_sha256', sa.Text(), nullable=False),
    sa.Column('signed_off_by_user_id', sa.UUID(), nullable=False),
    sa.Column('job_title_at_time', sa.Text(), nullable=False),
    sa.Column('signed_off_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("job_title_at_time IN ('clinician', 'trial_coordinator', 'secretary')", name=op.f('ck_export_job_title_at_time_allowed')),
    sa.CheckConstraint("kind IN ('identified', 'deidentified')", name=op.f('ck_export_kind_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_export_soft_delete')),
    sa.CheckConstraint('num_nonnulls(patient_id, redaction_job_id) >= 1', name=op.f('ck_export_has_subject')),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_export_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_export_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recipient_provider_id', 'practice_id'], ['provider.id', 'provider.practice_id'], name=op.f('fk_export_recipient_provider_id_practice_id'), ondelete='SET NULL (recipient_provider_id)'),
    sa.ForeignKeyConstraint(['redaction_job_id', 'practice_id'], ['redaction_job.id', 'redaction_job.practice_id'], name=op.f('fk_export_redaction_job_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['report_id', 'practice_id'], ['report.id', 'report.practice_id'], name=op.f('fk_export_report_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['signed_off_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_export_signed_off_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_export')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_export_id_practice_id'))
    )
    op.create_index(op.f('ix_export_deleted_by_user_id'), 'export', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_export_patient_id'), 'export', ['patient_id'], unique=False)
    op.create_index(op.f('ix_export_practice_id'), 'export', ['practice_id'], unique=False)
    op.create_index(op.f('ix_export_recipient_provider_id'), 'export', ['recipient_provider_id'], unique=False)
    op.create_index(op.f('ix_export_redaction_job_id'), 'export', ['redaction_job_id'], unique=False)
    op.create_index(op.f('ix_export_report_id'), 'export', ['report_id'], unique=False)
    op.create_index(op.f('ix_export_signed_off_by_user_id'), 'export', ['signed_off_by_user_id'], unique=False)
    op.create_table('medication_change_log',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('medication_id', sa.UUID(), nullable=False),
    sa.Column('change_type', sa.Text(), nullable=False),
    sa.Column('previous_value', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('new_value', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('changed_by_user_id', sa.UUID(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("change_type IN ('added', 'dose_changed', 'discontinued', 'restarted', 'status_changed', 'verified', 'corrected')", name=op.f('ck_medication_change_log_change_type_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_medication_change_log_soft_delete')),
    sa.ForeignKeyConstraint(['changed_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_medication_change_log_changed_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['medication_id', 'practice_id'], ['medication.id', 'medication.practice_id'], name=op.f('fk_medication_change_log_medication_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_medication_change_log_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_medication_change_log')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_medication_change_log_id_practice_id')),
    info={'immutable': True}
    )
    op.create_index(op.f('ix_medication_change_log_changed_by_user_id'), 'medication_change_log', ['changed_by_user_id'], unique=False)
    op.create_index(op.f('ix_medication_change_log_deleted_by_user_id'), 'medication_change_log', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_medication_change_log_medication_id'), 'medication_change_log', ['medication_id'], unique=False)
    op.create_index(op.f('ix_medication_change_log_practice_id'), 'medication_change_log', ['practice_id'], unique=False)
    op.create_foreign_key(op.f('fk_llm_cache_deleted_by_user_id'), 'llm_cache', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_pbs_item_deleted_by_user_id'), 'pbs_item', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_pbs_refresh_log_deleted_by_user_id'), 'pbs_refresh_log', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_practice_deleted_by_user_id'), 'practice', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_specialty_module_deleted_by_user_id'), 'specialty_module', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_trial_snapshot_deleted_by_user_id'), 'trial_snapshot', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_document_type_deleted_by_user_id'), 'document_type', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_drug_reference_deleted_by_user_id'), 'drug_reference', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_fact_kind_deleted_by_user_id'), 'fact_kind', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_job_kind_deleted_by_user_id'), 'job_kind', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_patient_deleted_by_user_id_practice_id'), 'patient', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_pipeline_run_deleted_by_user_id'), 'pipeline_run', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_provider_deleted_by_user_id_practice_id'), 'provider', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_trial_deleted_by_user_id'), 'trial', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_care_team_member_deleted_by_user_id_practice_id'), 'care_team_member', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_patient_identity_deleted_by_user_id_practice_id'), 'patient_identity', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], source_schema='identity', ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_job_deleted_by_user_id'), 'job', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_trial_criterion_deleted_by_user_id'), 'trial_criterion', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_trial_site_deleted_by_user_id'), 'trial_site', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_user_deleted_by_user_id_practice_id'), 'user', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_document_deleted_by_user_id_practice_id'), 'document', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_job_step_deleted_by_user_id'), 'job_step', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_next_step_deleted_by_user_id_practice_id'), 'next_step', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_practice_module_deleted_by_user_id_practice_id'), 'practice_module', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_redaction_job_deleted_by_user_id_practice_id'), 'redaction_job', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_verification_deleted_by_user_id_practice_id'), 'verification', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_cloud_request_deleted_by_user_id'), 'cloud_request', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_extraction_deleted_by_user_id_practice_id'), 'extraction', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_redaction_job_file_deleted_by_user_id_practice_id'), 'redaction_job_file', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_extracted_fact_deleted_by_user_id_practice_id'), 'extracted_fact', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_llm_call_log_deleted_by_user_id'), 'llm_call_log', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_ocr_page_deleted_by_user_id_practice_id'), 'ocr_page', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_redaction_log_deleted_by_user_id_practice_id'), 'redaction_log', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_clinical_note_deleted_by_user_id_practice_id'), 'clinical_note', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_condition_deleted_by_user_id_practice_id'), 'condition', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_imaging_study_deleted_by_user_id_practice_id'), 'imaging_study', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_lab_result_deleted_by_user_id_practice_id'), 'lab_result', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_management_plan_deleted_by_user_id_practice_id'), 'management_plan', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_redaction_entity_deleted_by_user_id_practice_id'), 'redaction_entity', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_finding_deleted_by_user_id_practice_id'), 'finding', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_match_run_deleted_by_user_id_practice_id'), 'match_run', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_treatment_course_deleted_by_user_id_practice_id'), 'treatment_course', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_match_result_deleted_by_user_id_practice_id'), 'match_result', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_medication_deleted_by_user_id_practice_id'), 'medication', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_report_deleted_by_user_id_practice_id'), 'report', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_criterion_evaluation_deleted_by_user_id_practice_id'), 'criterion_evaluation', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_export_deleted_by_user_id_practice_id'), 'export', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_medication_change_log_deleted_by_user_id_practice_id'), 'medication_change_log', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')

    create_functions()
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER set_updated_at BEFORE UPDATE ON {quoted(table)}"
            " FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )
    for table in IMMUTABLE_TABLES:
        op.execute(
            f"CREATE TRIGGER reject_change BEFORE UPDATE OR DELETE ON {quoted(table)}"
            " FOR EACH ROW EXECUTE FUNCTION reject_change()"
        )
        op.execute(
            f"CREATE TRIGGER reject_truncate BEFORE TRUNCATE ON {quoted(table)}"
            " FOR EACH STATEMENT EXECUTE FUNCTION reject_change()"
        )
    op.execute(
        "CREATE TRIGGER record_reply_only BEFORE UPDATE OR DELETE ON cloud_request"
        " FOR EACH ROW EXECUTE FUNCTION cloud_request_record_reply_only()"
    )

    for table in APP_DELETABLE_TABLES:
        op.execute(f"GRANT DELETE ON {quoted(table)} TO vigil_app")
    for table in SUPPORT_READABLE_TABLES:
        op.execute(f"GRANT SELECT ON {quoted(table)} TO vigil_support")

    op.execute(
        "INSERT INTO fact_kind (key, module_key, record_table) VALUES "
        + ", ".join(f"('{kind}', NULL, '{kind}')" for kind in CORE_FACT_KINDS)
    )


def create_functions() -> None:
    op.execute(
        """
        CREATE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% on % is not allowed: rows never change once written', TG_OP, TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    # The cloud request ledger is written before sending; afterwards only the reply may be recorded.
    op.execute(
        """
        CREATE FUNCTION cloud_request_record_reply_only() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            reply_columns text[] := ARRAY['status', 'sent_at', 'response_received_at', 'updated_at'];
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'DELETE on cloud_request is not allowed: the ledger is permanent'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF (to_jsonb(NEW) - reply_columns) IS DISTINCT FROM (to_jsonb(OLD) - reply_columns) THEN
                RAISE EXCEPTION 'cloud_request may only be updated to record the reply (status, sent_at, response_received_at)'
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END $$
        """
    )


def downgrade() -> None:
    op.drop_constraint('fk_llm_cache_deleted_by_user_id', 'llm_cache', type_='foreignkey')
    op.drop_constraint('fk_pbs_item_deleted_by_user_id', 'pbs_item', type_='foreignkey')
    op.drop_constraint('fk_pbs_refresh_log_deleted_by_user_id', 'pbs_refresh_log', type_='foreignkey')
    op.drop_constraint('fk_practice_deleted_by_user_id', 'practice', type_='foreignkey')
    op.drop_constraint('fk_specialty_module_deleted_by_user_id', 'specialty_module', type_='foreignkey')
    op.drop_constraint('fk_trial_snapshot_deleted_by_user_id', 'trial_snapshot', type_='foreignkey')
    op.drop_constraint('fk_document_type_deleted_by_user_id', 'document_type', type_='foreignkey')
    op.drop_constraint('fk_drug_reference_deleted_by_user_id', 'drug_reference', type_='foreignkey')
    op.drop_constraint('fk_fact_kind_deleted_by_user_id', 'fact_kind', type_='foreignkey')
    op.drop_constraint('fk_job_kind_deleted_by_user_id', 'job_kind', type_='foreignkey')
    op.drop_constraint('fk_patient_deleted_by_user_id_practice_id', 'patient', type_='foreignkey')
    op.drop_constraint('fk_pipeline_run_deleted_by_user_id', 'pipeline_run', type_='foreignkey')
    op.drop_constraint('fk_provider_deleted_by_user_id_practice_id', 'provider', type_='foreignkey')
    op.drop_constraint('fk_trial_deleted_by_user_id', 'trial', type_='foreignkey')
    op.drop_constraint('fk_care_team_member_deleted_by_user_id_practice_id', 'care_team_member', type_='foreignkey')
    op.drop_constraint('fk_patient_identity_deleted_by_user_id_practice_id', 'patient_identity', type_='foreignkey', schema='identity')
    op.drop_constraint('fk_job_deleted_by_user_id', 'job', type_='foreignkey')
    op.drop_constraint('fk_trial_criterion_deleted_by_user_id', 'trial_criterion', type_='foreignkey')
    op.drop_constraint('fk_trial_site_deleted_by_user_id', 'trial_site', type_='foreignkey')
    op.drop_constraint('fk_user_deleted_by_user_id_practice_id', 'user', type_='foreignkey')
    op.drop_constraint('fk_document_deleted_by_user_id_practice_id', 'document', type_='foreignkey')
    op.drop_constraint('fk_job_step_deleted_by_user_id', 'job_step', type_='foreignkey')
    op.drop_constraint('fk_next_step_deleted_by_user_id_practice_id', 'next_step', type_='foreignkey')
    op.drop_constraint('fk_practice_module_deleted_by_user_id_practice_id', 'practice_module', type_='foreignkey')
    op.drop_constraint('fk_redaction_job_deleted_by_user_id_practice_id', 'redaction_job', type_='foreignkey')
    op.drop_constraint('fk_verification_deleted_by_user_id_practice_id', 'verification', type_='foreignkey')
    op.drop_constraint('fk_cloud_request_deleted_by_user_id', 'cloud_request', type_='foreignkey')
    op.drop_constraint('fk_extraction_deleted_by_user_id_practice_id', 'extraction', type_='foreignkey')
    op.drop_constraint('fk_redaction_job_file_deleted_by_user_id_practice_id', 'redaction_job_file', type_='foreignkey')
    op.drop_constraint('fk_extracted_fact_deleted_by_user_id_practice_id', 'extracted_fact', type_='foreignkey')
    op.drop_constraint('fk_llm_call_log_deleted_by_user_id', 'llm_call_log', type_='foreignkey')
    op.drop_constraint('fk_ocr_page_deleted_by_user_id_practice_id', 'ocr_page', type_='foreignkey')
    op.drop_constraint('fk_redaction_log_deleted_by_user_id_practice_id', 'redaction_log', type_='foreignkey')
    op.drop_constraint('fk_clinical_note_deleted_by_user_id_practice_id', 'clinical_note', type_='foreignkey')
    op.drop_constraint('fk_condition_deleted_by_user_id_practice_id', 'condition', type_='foreignkey')
    op.drop_constraint('fk_imaging_study_deleted_by_user_id_practice_id', 'imaging_study', type_='foreignkey')
    op.drop_constraint('fk_lab_result_deleted_by_user_id_practice_id', 'lab_result', type_='foreignkey')
    op.drop_constraint('fk_management_plan_deleted_by_user_id_practice_id', 'management_plan', type_='foreignkey')
    op.drop_constraint('fk_redaction_entity_deleted_by_user_id_practice_id', 'redaction_entity', type_='foreignkey')
    op.drop_constraint('fk_finding_deleted_by_user_id_practice_id', 'finding', type_='foreignkey')
    op.drop_constraint('fk_match_run_deleted_by_user_id_practice_id', 'match_run', type_='foreignkey')
    op.drop_constraint('fk_treatment_course_deleted_by_user_id_practice_id', 'treatment_course', type_='foreignkey')
    op.drop_constraint('fk_match_result_deleted_by_user_id_practice_id', 'match_result', type_='foreignkey')
    op.drop_constraint('fk_medication_deleted_by_user_id_practice_id', 'medication', type_='foreignkey')
    op.drop_constraint('fk_report_deleted_by_user_id_practice_id', 'report', type_='foreignkey')
    op.drop_constraint('fk_criterion_evaluation_deleted_by_user_id_practice_id', 'criterion_evaluation', type_='foreignkey')
    op.drop_constraint('fk_export_deleted_by_user_id_practice_id', 'export', type_='foreignkey')
    op.drop_constraint('fk_medication_change_log_deleted_by_user_id_practice_id', 'medication_change_log', type_='foreignkey')
    op.drop_index(op.f('ix_medication_change_log_practice_id'), table_name='medication_change_log')
    op.drop_index(op.f('ix_medication_change_log_medication_id'), table_name='medication_change_log')
    op.drop_index(op.f('ix_medication_change_log_deleted_by_user_id'), table_name='medication_change_log')
    op.drop_index(op.f('ix_medication_change_log_changed_by_user_id'), table_name='medication_change_log')
    op.drop_table('medication_change_log')
    op.drop_index(op.f('ix_export_signed_off_by_user_id'), table_name='export')
    op.drop_index(op.f('ix_export_report_id'), table_name='export')
    op.drop_index(op.f('ix_export_redaction_job_id'), table_name='export')
    op.drop_index(op.f('ix_export_recipient_provider_id'), table_name='export')
    op.drop_index(op.f('ix_export_practice_id'), table_name='export')
    op.drop_index(op.f('ix_export_patient_id'), table_name='export')
    op.drop_index(op.f('ix_export_deleted_by_user_id'), table_name='export')
    op.drop_table('export')
    op.drop_index(op.f('ix_criterion_evaluation_trial_criterion_id'), table_name='criterion_evaluation')
    op.drop_index(op.f('ix_criterion_evaluation_practice_id'), table_name='criterion_evaluation')
    op.drop_index(op.f('ix_criterion_evaluation_match_result_id'), table_name='criterion_evaluation')
    op.drop_index(op.f('ix_criterion_evaluation_deleted_by_user_id'), table_name='criterion_evaluation')
    op.drop_table('criterion_evaluation')
    op.drop_index(op.f('ix_report_practice_id'), table_name='report')
    op.drop_index(op.f('ix_report_patient_id'), table_name='report')
    op.drop_index(op.f('ix_report_match_run_id'), table_name='report')
    op.drop_index(op.f('ix_report_deleted_by_user_id'), table_name='report')
    op.drop_table('report')
    op.drop_index(op.f('ix_medication_treatment_course_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_source_fact_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_source_document_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_prescribed_by_provider_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_practice_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_patient_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_entered_by_user_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_drug_reference_id'), table_name='medication')
    op.drop_index(op.f('ix_medication_deleted_by_user_id'), table_name='medication')
    op.drop_table('medication')
    op.drop_index(op.f('ix_match_result_trial_id'), table_name='match_result')
    op.drop_index(op.f('ix_match_result_practice_id'), table_name='match_result')
    op.drop_index(op.f('ix_match_result_match_run_id'), table_name='match_result')
    op.drop_index(op.f('ix_match_result_deleted_by_user_id'), table_name='match_result')
    op.drop_table('match_result')
    op.drop_index(op.f('ix_treatment_course_source_fact_id'), table_name='treatment_course')
    op.drop_index(op.f('ix_treatment_course_source_document_id'), table_name='treatment_course')
    op.drop_index(op.f('ix_treatment_course_practice_id'), table_name='treatment_course')
    op.drop_index(op.f('ix_treatment_course_entered_by_user_id'), table_name='treatment_course')
    op.drop_index(op.f('ix_treatment_course_deleted_by_user_id'), table_name='treatment_course')
    op.drop_index('ix_treatment_course_condition_id_start_date', table_name='treatment_course')
    op.drop_index(op.f('ix_treatment_course_condition_id'), table_name='treatment_course')
    op.drop_table('treatment_course')
    op.drop_index(op.f('ix_match_run_target_condition_id'), table_name='match_run')
    op.drop_index(op.f('ix_match_run_snapshot_id'), table_name='match_run')
    op.drop_index(op.f('ix_match_run_run_by_user_id'), table_name='match_run')
    op.drop_index(op.f('ix_match_run_practice_id'), table_name='match_run')
    op.drop_index(op.f('ix_match_run_patient_id'), table_name='match_run')
    op.drop_index('ix_match_run_latest', table_name='match_run')
    op.drop_index(op.f('ix_match_run_deleted_by_user_id'), table_name='match_run')
    op.drop_table('match_run')
    op.drop_index(op.f('ix_finding_source_fact_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_source_document_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_practice_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_patient_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_imaging_study_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_entered_by_user_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_deleted_by_user_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_condition_id'), table_name='finding')
    op.drop_table('finding')
    op.drop_index(op.f('ix_redaction_entity_redaction_log_id'), table_name='redaction_entity')
    op.drop_index(op.f('ix_redaction_entity_practice_id'), table_name='redaction_entity')
    op.drop_index(op.f('ix_redaction_entity_deleted_by_user_id'), table_name='redaction_entity')
    op.drop_table('redaction_entity')
    op.drop_index(op.f('ix_management_plan_source_fact_id'), table_name='management_plan')
    op.drop_index(op.f('ix_management_plan_source_document_id'), table_name='management_plan')
    op.drop_index(op.f('ix_management_plan_practice_id'), table_name='management_plan')
    op.drop_index(op.f('ix_management_plan_patient_id'), table_name='management_plan')
    op.drop_index(op.f('ix_management_plan_entered_by_user_id'), table_name='management_plan')
    op.drop_index(op.f('ix_management_plan_deleted_by_user_id'), table_name='management_plan')
    op.drop_index(op.f('ix_management_plan_authored_by_provider_id'), table_name='management_plan')
    op.drop_table('management_plan')
    op.drop_index(op.f('ix_lab_result_source_fact_id'), table_name='lab_result')
    op.drop_index(op.f('ix_lab_result_source_document_id'), table_name='lab_result')
    op.drop_index(op.f('ix_lab_result_practice_id'), table_name='lab_result')
    op.drop_index(op.f('ix_lab_result_patient_id'), table_name='lab_result')
    op.drop_index('ix_lab_result_patient_analyte_collected', table_name='lab_result')
    op.drop_index(op.f('ix_lab_result_entered_by_user_id'), table_name='lab_result')
    op.drop_index(op.f('ix_lab_result_deleted_by_user_id'), table_name='lab_result')
    op.drop_table('lab_result')
    op.drop_index(op.f('ix_imaging_study_source_fact_id'), table_name='imaging_study')
    op.drop_index(op.f('ix_imaging_study_source_document_id'), table_name='imaging_study')
    op.drop_index(op.f('ix_imaging_study_practice_id'), table_name='imaging_study')
    op.drop_index('ix_imaging_study_patient_modality_date', table_name='imaging_study')
    op.drop_index(op.f('ix_imaging_study_patient_id'), table_name='imaging_study')
    op.drop_index(op.f('ix_imaging_study_entered_by_user_id'), table_name='imaging_study')
    op.drop_index(op.f('ix_imaging_study_deleted_by_user_id'), table_name='imaging_study')
    op.drop_table('imaging_study')
    op.drop_index(op.f('ix_condition_source_fact_id'), table_name='condition')
    op.drop_index(op.f('ix_condition_source_document_id'), table_name='condition')
    op.drop_index(op.f('ix_condition_practice_id'), table_name='condition')
    op.drop_index('ix_condition_patient_id_status', table_name='condition')
    op.drop_index(op.f('ix_condition_patient_id'), table_name='condition')
    op.drop_index(op.f('ix_condition_extended_by_module'), table_name='condition')
    op.drop_index(op.f('ix_condition_entered_by_user_id'), table_name='condition')
    op.drop_index(op.f('ix_condition_deleted_by_user_id'), table_name='condition')
    op.drop_table('condition')
    op.drop_index(op.f('ix_clinical_note_source_fact_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_source_document_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_recipient_provider_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_practice_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_patient_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_entered_by_user_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_deleted_by_user_id'), table_name='clinical_note')
    op.drop_index(op.f('ix_clinical_note_author_provider_id'), table_name='clinical_note')
    op.drop_table('clinical_note')
    op.drop_index(op.f('ix_redaction_log_reviewed_by_user_id'), table_name='redaction_log')
    op.drop_index(op.f('ix_redaction_log_redaction_job_file_id'), table_name='redaction_log')
    op.drop_index(op.f('ix_redaction_log_practice_id'), table_name='redaction_log')
    op.drop_index(op.f('ix_redaction_log_pipeline_run_id'), table_name='redaction_log')
    op.drop_index(op.f('ix_redaction_log_document_id'), table_name='redaction_log')
    op.drop_index(op.f('ix_redaction_log_deleted_by_user_id'), table_name='redaction_log')
    op.drop_table('redaction_log')
    op.drop_index(op.f('ix_ocr_page_redaction_job_file_id'), table_name='ocr_page')
    op.drop_index(op.f('ix_ocr_page_practice_id'), table_name='ocr_page')
    op.drop_index(op.f('ix_ocr_page_document_id'), table_name='ocr_page')
    op.drop_index(op.f('ix_ocr_page_deleted_by_user_id'), table_name='ocr_page')
    op.drop_table('ocr_page')
    op.drop_index(op.f('ix_llm_call_log_practice_id'), table_name='llm_call_log')
    op.drop_index(op.f('ix_llm_call_log_deleted_by_user_id'), table_name='llm_call_log')
    op.drop_index(op.f('ix_llm_call_log_cloud_request_id'), table_name='llm_call_log')
    op.drop_table('llm_call_log')
    op.drop_index('ix_extracted_fact_review_queue', table_name='extracted_fact')
    op.drop_index(op.f('ix_extracted_fact_practice_id'), table_name='extracted_fact')
    op.drop_index(op.f('ix_extracted_fact_patient_id'), table_name='extracted_fact')
    op.drop_index(op.f('ix_extracted_fact_module_key'), table_name='extracted_fact')
    op.drop_index(op.f('ix_extracted_fact_fact_kind'), table_name='extracted_fact')
    op.drop_index(op.f('ix_extracted_fact_extraction_id'), table_name='extracted_fact')
    op.drop_index(op.f('ix_extracted_fact_deleted_by_user_id'), table_name='extracted_fact')
    op.drop_table('extracted_fact')
    op.drop_index(op.f('ix_redaction_job_file_redaction_job_id'), table_name='redaction_job_file')
    op.drop_index(op.f('ix_redaction_job_file_practice_id'), table_name='redaction_job_file')
    op.drop_index(op.f('ix_redaction_job_file_deleted_by_user_id'), table_name='redaction_job_file')
    op.drop_table('redaction_job_file')
    op.drop_index(op.f('ix_extraction_practice_id'), table_name='extraction')
    op.drop_index(op.f('ix_extraction_pipeline_run_id'), table_name='extraction')
    op.drop_index(op.f('ix_extraction_document_type_id'), table_name='extraction')
    op.drop_index(op.f('ix_extraction_document_id'), table_name='extraction')
    op.drop_index(op.f('ix_extraction_deleted_by_user_id'), table_name='extraction')
    op.drop_table('extraction')
    op.drop_index(op.f('ix_cloud_request_practice_id'), table_name='cloud_request')
    op.drop_index(op.f('ix_cloud_request_initiated_by_user_id'), table_name='cloud_request')
    op.drop_index(op.f('ix_cloud_request_document_id'), table_name='cloud_request')
    op.drop_index(op.f('ix_cloud_request_deleted_by_user_id'), table_name='cloud_request')
    op.drop_table('cloud_request')
    op.drop_index(op.f('ix_verification_user_id'), table_name='verification')
    op.drop_index('ix_verification_subject', table_name='verification')
    op.drop_index(op.f('ix_verification_practice_id'), table_name='verification')
    op.drop_index(op.f('ix_verification_deleted_by_user_id'), table_name='verification')
    op.drop_table('verification')
    op.drop_index(op.f('ix_redaction_job_practice_id'), table_name='redaction_job')
    op.drop_index(op.f('ix_redaction_job_patient_id'), table_name='redaction_job')
    op.drop_index(op.f('ix_redaction_job_deleted_by_user_id'), table_name='redaction_job')
    op.drop_index(op.f('ix_redaction_job_created_by_user_id'), table_name='redaction_job')
    op.drop_table('redaction_job')
    op.drop_index(op.f('ix_practice_module_practice_id'), table_name='practice_module')
    op.drop_index(op.f('ix_practice_module_module_key'), table_name='practice_module')
    op.drop_index(op.f('ix_practice_module_deleted_by_user_id'), table_name='practice_module')
    op.drop_index(op.f('ix_practice_module_changed_by_user_id'), table_name='practice_module')
    op.drop_table('practice_module')
    op.drop_index(op.f('ix_next_step_practice_id'), table_name='next_step')
    op.drop_index(op.f('ix_next_step_patient_id'), table_name='next_step')
    op.drop_index(op.f('ix_next_step_done_by_user_id'), table_name='next_step')
    op.drop_index(op.f('ix_next_step_deleted_by_user_id'), table_name='next_step')
    op.drop_index(op.f('ix_next_step_created_by_user_id'), table_name='next_step')
    op.drop_table('next_step')
    op.drop_index(op.f('ix_job_step_job_id'), table_name='job_step')
    op.drop_index(op.f('ix_job_step_deleted_by_user_id'), table_name='job_step')
    op.drop_table('job_step')
    op.drop_index(op.f('ix_document_uploaded_by_user_id'), table_name='document')
    op.drop_index(op.f('ix_document_practice_id'), table_name='document')
    op.drop_index('ix_document_patient_id_doc_date', table_name='document')
    op.drop_index(op.f('ix_document_patient_id'), table_name='document')
    op.drop_index(op.f('ix_document_held_by_user_id'), table_name='document')
    op.drop_index('ix_document_held', table_name='document', postgresql_where=sa.text("status = 'held'"))
    op.drop_index(op.f('ix_document_document_type_id'), table_name='document')
    op.drop_index(op.f('ix_document_deleted_by_user_id'), table_name='document')
    op.drop_table('document')
    op.drop_index(op.f('ix_user_provider_id'), table_name='user')
    op.drop_index(op.f('ix_user_practice_id'), table_name='user')
    op.drop_index(op.f('ix_user_deleted_by_user_id'), table_name='user')
    op.drop_table('user')
    op.drop_index(op.f('ix_trial_site_trial_id'), table_name='trial_site')
    op.drop_index(op.f('ix_trial_site_deleted_by_user_id'), table_name='trial_site')
    op.drop_index('ix_trial_site_country_city', table_name='trial_site')
    op.drop_table('trial_site')
    op.drop_index(op.f('ix_trial_criterion_trial_id'), table_name='trial_criterion')
    op.drop_index(op.f('ix_trial_criterion_deleted_by_user_id'), table_name='trial_criterion')
    op.drop_table('trial_criterion')
    op.drop_index(op.f('ix_job_practice_id'), table_name='job')
    op.drop_index(op.f('ix_job_pipeline_run_id'), table_name='job')
    op.drop_index(op.f('ix_job_kind'), table_name='job')
    op.drop_index(op.f('ix_job_deleted_by_user_id'), table_name='job')
    op.drop_index('ix_job_claim', table_name='job')
    op.drop_table('job')
    op.drop_index(op.f('ix_patient_identity_practice_id'), table_name='patient_identity', schema='identity')
    op.drop_index(op.f('ix_patient_identity_deleted_by_user_id'), table_name='patient_identity', schema='identity')
    op.drop_table('patient_identity', schema='identity')
    op.drop_index(op.f('ix_care_team_member_provider_id'), table_name='care_team_member')
    op.drop_index(op.f('ix_care_team_member_practice_id'), table_name='care_team_member')
    op.drop_index(op.f('ix_care_team_member_patient_id'), table_name='care_team_member')
    op.drop_index(op.f('ix_care_team_member_deleted_by_user_id'), table_name='care_team_member')
    op.drop_table('care_team_member')
    op.drop_index(op.f('ix_trial_snapshot_id'), table_name='trial')
    op.drop_index(op.f('ix_trial_deleted_by_user_id'), table_name='trial')
    op.drop_index('ix_trial_conditions', table_name='trial', postgresql_using='gin')
    op.drop_table('trial')
    op.drop_index('uq_provider_practice_id_provider_number', table_name='provider', postgresql_where=sa.text('provider_number IS NOT NULL'))
    op.drop_index(op.f('ix_provider_practice_id'), table_name='provider')
    op.drop_index(op.f('ix_provider_deleted_by_user_id'), table_name='provider')
    op.drop_table('provider')
    op.drop_index(op.f('ix_pipeline_run_practice_id'), table_name='pipeline_run')
    op.drop_index(op.f('ix_pipeline_run_deleted_by_user_id'), table_name='pipeline_run')
    op.drop_table('pipeline_run')
    op.drop_index(op.f('ix_patient_practice_id'), table_name='patient')
    op.drop_index('ix_patient_not_deleted', table_name='patient', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index(op.f('ix_patient_deleted_by_user_id'), table_name='patient')
    op.drop_table('patient')
    op.drop_index(op.f('ix_job_kind_module_key'), table_name='job_kind')
    op.drop_index(op.f('ix_job_kind_deleted_by_user_id'), table_name='job_kind')
    op.drop_table('job_kind')
    op.drop_index(op.f('ix_fact_kind_module_key'), table_name='fact_kind')
    op.drop_index(op.f('ix_fact_kind_deleted_by_user_id'), table_name='fact_kind')
    op.drop_table('fact_kind')
    op.drop_index(op.f('ix_drug_reference_pbs_item_id'), table_name='drug_reference')
    op.drop_index(op.f('ix_drug_reference_deleted_by_user_id'), table_name='drug_reference')
    op.drop_table('drug_reference')
    op.drop_index(op.f('ix_document_type_module_key'), table_name='document_type')
    op.drop_index(op.f('ix_document_type_deleted_by_user_id'), table_name='document_type')
    op.drop_table('document_type')
    op.drop_index(op.f('ix_trial_snapshot_deleted_by_user_id'), table_name='trial_snapshot')
    op.drop_table('trial_snapshot')
    op.drop_index(op.f('ix_specialty_module_deleted_by_user_id'), table_name='specialty_module')
    op.drop_table('specialty_module')
    op.drop_index(op.f('ix_practice_deleted_by_user_id'), table_name='practice')
    op.drop_table('practice')
    op.drop_index(op.f('ix_pbs_refresh_log_deleted_by_user_id'), table_name='pbs_refresh_log')
    op.drop_table('pbs_refresh_log')
    op.drop_index(op.f('ix_pbs_item_deleted_by_user_id'), table_name='pbs_item')
    op.drop_table('pbs_item')
    op.drop_index(op.f('ix_llm_cache_deleted_by_user_id'), table_name='llm_cache')
    op.drop_table('llm_cache')

    op.execute("DROP FUNCTION cloud_request_record_reply_only()")
    op.execute("DROP FUNCTION reject_change()")
    op.execute("DROP FUNCTION set_updated_at()")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE ON TABLES FROM vigil_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA identity"
        " REVOKE SELECT, INSERT, UPDATE ON TABLES FROM identity_access"
    )
    op.execute("DROP SCHEMA identity")
