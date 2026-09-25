"""Oncology module baseline: its tables, the Line of Therapy rule and its registry rows.

Design doc §4.1, §6.2–§6.3. The Oncology module's tables may reference Core tables; the Core never
references these. Frozen once merged. The table-creation section was generated from the models.

Revision ID: 0002_oncology
Revises: 0001_core
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import Text

revision = "0002_oncology"
down_revision = "0001_core"
branch_labels = None
depends_on = None

TABLES = (
    'cancer_type',
    'eviq_refresh_log',
    'treatment_protocol',
    'protocol_drug',
    'cns_status',
    'performance_status',
    'cancer_diagnosis',
    'biomarker',
    'oncology_course_detail',
    'recurrence',
    'response_assessment',
)

ONCOLOGY_FACT_KINDS = (
    "cancer_diagnosis",
    "recurrence",
    "biomarker",
    "response_assessment",
    "performance_status",
    "cns_status",
)


def upgrade() -> None:
    op.execute(
        "INSERT INTO specialty_module (key, display_name, version) VALUES ('oncology', 'Oncology', '0.1.0')"
    )
    op.create_table('cancer_type',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=False),
    sa.Column('icd10_codes', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('staging_systems', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_cancer_type_soft_delete')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cancer_type')),
    sa.UniqueConstraint('key', name=op.f('uq_cancer_type_key'))
    )
    op.create_index(op.f('ix_cancer_type_deleted_by_user_id'), 'cancer_type', ['deleted_by_user_id'], unique=False)
    op.create_table('eviq_refresh_log',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('refreshed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('item_count', sa.Integer(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('succeeded', 'partial', 'failed')", name=op.f('ck_eviq_refresh_log_status_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_eviq_refresh_log_soft_delete')),
    sa.CheckConstraint('item_count IS NULL OR item_count >= 0', name=op.f('ck_eviq_refresh_log_item_count')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_eviq_refresh_log'))
    )
    op.create_index(op.f('ix_eviq_refresh_log_deleted_by_user_id'), 'eviq_refresh_log', ['deleted_by_user_id'], unique=False)
    op.create_table('treatment_protocol',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('cancer_type_id', sa.UUID(), nullable=False),
    sa.Column('protocol_name', sa.Text(), nullable=False),
    sa.Column('intent', sa.Text(), nullable=True),
    sa.Column('line_of_therapy', sa.Integer(), nullable=True),
    sa.Column('disease_extent_required', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('biomarker_requirements', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('eviq_id', sa.Text(), nullable=True),
    sa.Column('eviq_url', sa.Text(), nullable=True),
    sa.Column('eviq_version', sa.Text(), nullable=True),
    sa.Column('eviq_updated_on', sa.Date(), nullable=True),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('evidence_level', sa.Text(), nullable=True),
    sa.Column('raw_data', postgresql.JSONB(astext_type=Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("intent IN ('curative', 'neoadjuvant', 'adjuvant', 'palliative')", name=op.f('ck_treatment_protocol_intent_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_treatment_protocol_soft_delete')),
    sa.CheckConstraint('line_of_therapy IS NULL OR line_of_therapy >= 1', name=op.f('ck_treatment_protocol_line_positive')),
    sa.ForeignKeyConstraint(['cancer_type_id'], ['cancer_type.id'], name=op.f('fk_treatment_protocol_cancer_type_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_treatment_protocol'))
    )
    op.create_index(op.f('ix_treatment_protocol_cancer_type_id'), 'treatment_protocol', ['cancer_type_id'], unique=False)
    op.create_index(op.f('ix_treatment_protocol_deleted_by_user_id'), 'treatment_protocol', ['deleted_by_user_id'], unique=False)
    op.create_table('protocol_drug',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('treatment_protocol_id', sa.UUID(), nullable=False),
    sa.Column('drug_name', sa.Text(), nullable=False),
    sa.Column('generic_name', sa.Text(), nullable=True),
    sa.Column('role', sa.Text(), nullable=True),
    sa.Column('route', sa.Text(), nullable=True),
    sa.Column('pbs_item_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("role IN ('backbone', 'combination', 'maintenance')", name=op.f('ck_protocol_drug_role_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_protocol_drug_soft_delete')),
    sa.ForeignKeyConstraint(['pbs_item_id'], ['pbs_item.id'], name=op.f('fk_protocol_drug_pbs_item_id'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['treatment_protocol_id'], ['treatment_protocol.id'], name=op.f('fk_protocol_drug_treatment_protocol_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_protocol_drug'))
    )
    op.create_index(op.f('ix_protocol_drug_deleted_by_user_id'), 'protocol_drug', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_protocol_drug_pbs_item_id'), 'protocol_drug', ['pbs_item_id'], unique=False)
    op.create_index(op.f('ix_protocol_drug_treatment_protocol_id'), 'protocol_drug', ['treatment_protocol_id'], unique=False)
    op.create_table('cns_status',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('present', sa.Boolean(), nullable=True),
    sa.Column('lesion_count', sa.Integer(), nullable=True),
    sa.Column('locations', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('treated', sa.Boolean(), nullable=True),
    sa.Column('treatment_type', sa.Text(), nullable=True),
    sa.Column('symptomatic', sa.Boolean(), nullable=True),
    sa.Column('on_steroids', sa.Boolean(), nullable=True),
    sa.Column('steroid_dose_mg', sa.Numeric(), nullable=True),
    sa.Column('leptomeningeal', sa.Boolean(), nullable=True),
    sa.Column('assessed_on', sa.Date(), nullable=False),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_cns_status_soft_delete')),
    sa.CheckConstraint('lesion_count IS NULL OR lesion_count >= 0', name=op.f('ck_cns_status_lesion_count')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_cns_status_provenance')),
    sa.CheckConstraint('steroid_dose_mg IS NULL OR steroid_dose_mg >= 0', name=op.f('ck_cns_status_steroid_dose')),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_cns_status_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_cns_status_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_cns_status_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_cns_status_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_cns_status_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cns_status')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_cns_status_id_practice_id'))
    )
    op.create_index(op.f('ix_cns_status_deleted_by_user_id'), 'cns_status', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_cns_status_entered_by_user_id'), 'cns_status', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_cns_status_patient_id'), 'cns_status', ['patient_id'], unique=False)
    op.create_index(op.f('ix_cns_status_practice_id'), 'cns_status', ['practice_id'], unique=False)
    op.create_index(op.f('ix_cns_status_source_document_id'), 'cns_status', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_cns_status_source_fact_id'), 'cns_status', ['source_fact_id'], unique=False)
    op.create_table('performance_status',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('scale', sa.Text(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.Column('assessed_on', sa.Date(), nullable=False),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("(scale = 'ECOG' AND value BETWEEN 0 AND 5) OR (scale = 'KPS' AND value BETWEEN 0 AND 100 AND value % 10 = 0)", name=op.f('ck_performance_status_value_in_scale')),
    sa.CheckConstraint("scale IN ('ECOG', 'KPS')", name=op.f('ck_performance_status_scale_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_performance_status_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_performance_status_provenance')),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_performance_status_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_performance_status_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_performance_status_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_performance_status_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_performance_status_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_performance_status')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_performance_status_id_practice_id'))
    )
    op.create_index(op.f('ix_performance_status_deleted_by_user_id'), 'performance_status', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_performance_status_entered_by_user_id'), 'performance_status', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_performance_status_patient_id'), 'performance_status', ['patient_id'], unique=False)
    op.create_index(op.f('ix_performance_status_practice_id'), 'performance_status', ['practice_id'], unique=False)
    op.create_index(op.f('ix_performance_status_source_document_id'), 'performance_status', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_performance_status_source_fact_id'), 'performance_status', ['source_fact_id'], unique=False)
    op.create_table('cancer_diagnosis',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('condition_id', sa.UUID(), nullable=False),
    sa.Column('cancer_type_id', sa.UUID(), nullable=False),
    sa.Column('histology', sa.Text(), nullable=True),
    sa.Column('primary_site', sa.Text(), nullable=True),
    sa.Column('laterality', sa.Text(), nullable=True),
    sa.Column('dx_date', sa.Date(), nullable=True),
    sa.Column('stage_system', sa.Text(), nullable=True),
    sa.Column('stage', sa.Text(), nullable=True),
    sa.Column('disease_extent', sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
    sa.Column('disease_extent_as_of', sa.Date(), nullable=True),
    sa.Column('cancer_status', sa.Text(), server_default=sa.text("'unknown'"), nullable=False),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("cancer_status IN ('active', 'no_evidence_of_disease', 'unknown')", name=op.f('ck_cancer_diagnosis_cancer_status_allowed')),
    sa.CheckConstraint("disease_extent IN ('localised', 'locally_advanced', 'metastatic', 'unknown')", name=op.f('ck_cancer_diagnosis_disease_extent_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_cancer_diagnosis_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_cancer_diagnosis_provenance')),
    sa.ForeignKeyConstraint(['cancer_type_id'], ['cancer_type.id'], name=op.f('fk_cancer_diagnosis_cancer_type_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['condition_id', 'practice_id'], ['condition.id', 'condition.practice_id'], name=op.f('fk_cancer_diagnosis_condition_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_cancer_diagnosis_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_cancer_diagnosis_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_cancer_diagnosis_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_cancer_diagnosis_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cancer_diagnosis')),
    sa.UniqueConstraint('condition_id', name=op.f('uq_cancer_diagnosis_condition_id')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_cancer_diagnosis_id_practice_id'))
    )
    op.create_index(op.f('ix_cancer_diagnosis_cancer_type_id'), 'cancer_diagnosis', ['cancer_type_id'], unique=False)
    op.create_index(op.f('ix_cancer_diagnosis_deleted_by_user_id'), 'cancer_diagnosis', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_cancer_diagnosis_entered_by_user_id'), 'cancer_diagnosis', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_cancer_diagnosis_practice_id'), 'cancer_diagnosis', ['practice_id'], unique=False)
    op.create_index(op.f('ix_cancer_diagnosis_source_document_id'), 'cancer_diagnosis', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_cancer_diagnosis_source_fact_id'), 'cancer_diagnosis', ['source_fact_id'], unique=False)
    op.create_table('biomarker',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('cancer_diagnosis_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('variant', sa.Text(), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('value_num', sa.Numeric(), nullable=True),
    sa.Column('value_unit', sa.Text(), nullable=True),
    sa.Column('method', sa.Text(), nullable=True),
    sa.Column('specimen_site', sa.Text(), nullable=True),
    sa.Column('specimen_kind', sa.Text(), nullable=True),
    sa.Column('collected_on', sa.Date(), nullable=True),
    sa.Column('reported_on', sa.Date(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("method IN ('NGS', 'FISH', 'IHC', 'PCR', 'ctDNA')", name=op.f('ck_biomarker_method_allowed')),
    sa.CheckConstraint("specimen_kind IN ('primary', 'metastasis', 'liquid_biopsy')", name=op.f('ck_biomarker_specimen_kind_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_biomarker_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_biomarker_provenance')),
    sa.ForeignKeyConstraint(['cancer_diagnosis_id', 'practice_id'], ['cancer_diagnosis.id', 'cancer_diagnosis.practice_id'], name=op.f('fk_biomarker_cancer_diagnosis_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_biomarker_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_biomarker_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_biomarker_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_biomarker_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_biomarker')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_biomarker_id_practice_id'))
    )
    op.create_index(op.f('ix_biomarker_cancer_diagnosis_id'), 'biomarker', ['cancer_diagnosis_id'], unique=False)
    op.create_index(op.f('ix_biomarker_deleted_by_user_id'), 'biomarker', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_biomarker_entered_by_user_id'), 'biomarker', ['entered_by_user_id'], unique=False)
    op.create_index('ix_biomarker_latest', 'biomarker', ['cancer_diagnosis_id', 'name', sa.literal_column('collected_on DESC')], unique=False)
    op.create_index(op.f('ix_biomarker_practice_id'), 'biomarker', ['practice_id'], unique=False)
    op.create_index(op.f('ix_biomarker_source_document_id'), 'biomarker', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_biomarker_source_fact_id'), 'biomarker', ['source_fact_id'], unique=False)
    op.create_table('oncology_course_detail',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('treatment_course_id', sa.UUID(), nullable=False),
    sa.Column('line_of_therapy', sa.Integer(), nullable=True),
    sa.Column('treatment_protocol_id', sa.UUID(), nullable=True),
    sa.Column('best_response', sa.Text(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("best_response IN ('CR', 'PR', 'SD', 'PD', 'NE')", name=op.f('ck_oncology_course_detail_best_response_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_oncology_course_detail_soft_delete')),
    sa.CheckConstraint('line_of_therapy IS NULL OR line_of_therapy >= 1', name=op.f('ck_oncology_course_detail_line_positive')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_oncology_course_detail_provenance')),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_oncology_course_detail_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_oncology_course_detail_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_oncology_course_detail_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_oncology_course_detail_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['treatment_course_id', 'practice_id'], ['treatment_course.id', 'treatment_course.practice_id'], name=op.f('fk_oncology_course_detail_treatment_course_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['treatment_protocol_id'], ['treatment_protocol.id'], name=op.f('fk_oncology_course_detail_treatment_protocol_id'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_oncology_course_detail')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_oncology_course_detail_id_practice_id')),
    sa.UniqueConstraint('treatment_course_id', name=op.f('uq_oncology_course_detail_treatment_course_id'))
    )
    op.create_index(op.f('ix_oncology_course_detail_deleted_by_user_id'), 'oncology_course_detail', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_oncology_course_detail_entered_by_user_id'), 'oncology_course_detail', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_oncology_course_detail_practice_id'), 'oncology_course_detail', ['practice_id'], unique=False)
    op.create_index(op.f('ix_oncology_course_detail_source_document_id'), 'oncology_course_detail', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_oncology_course_detail_source_fact_id'), 'oncology_course_detail', ['source_fact_id'], unique=False)
    op.create_index(op.f('ix_oncology_course_detail_treatment_protocol_id'), 'oncology_course_detail', ['treatment_protocol_id'], unique=False)
    op.create_table('recurrence',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('cancer_diagnosis_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'suspected'"), nullable=False),
    sa.Column('detected_on', sa.Date(), nullable=True),
    sa.Column('extent', sa.Text(), nullable=True),
    sa.Column('sites', postgresql.JSONB(astext_type=Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('evidence_document_id', sa.UUID(), nullable=True),
    sa.Column('attributed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('attributed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('new_cancer_diagnosis_id', sa.UUID(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("(status = 'reclassified_as_new_primary') = (new_cancer_diagnosis_id IS NOT NULL)", name=op.f('ck_recurrence_new_primary_when_reclassified')),
    sa.CheckConstraint("extent IN ('local', 'regional', 'distant')", name=op.f('ck_recurrence_extent_allowed')),
    sa.CheckConstraint("status = 'suspected' OR attributed_by_user_id IS NOT NULL", name=op.f('ck_recurrence_attributed_unless_suspected')),
    sa.CheckConstraint("status IN ('suspected', 'confirmed', 'reclassified_as_new_primary')", name=op.f('ck_recurrence_status_allowed')),
    sa.CheckConstraint('(attributed_by_user_id IS NULL) = (attributed_at IS NULL)', name=op.f('ck_recurrence_attributed_together')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_recurrence_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_recurrence_provenance')),
    sa.ForeignKeyConstraint(['attributed_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_recurrence_attributed_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['cancer_diagnosis_id', 'practice_id'], ['cancer_diagnosis.id', 'cancer_diagnosis.practice_id'], name=op.f('fk_recurrence_cancer_diagnosis_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_recurrence_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['evidence_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_recurrence_evidence_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['new_cancer_diagnosis_id', 'practice_id'], ['cancer_diagnosis.id', 'cancer_diagnosis.practice_id'], name=op.f('fk_recurrence_new_cancer_diagnosis_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_recurrence_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_recurrence_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_recurrence_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recurrence')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_recurrence_id_practice_id'))
    )
    op.create_index(op.f('ix_recurrence_attributed_by_user_id'), 'recurrence', ['attributed_by_user_id'], unique=False)
    op.create_index(op.f('ix_recurrence_cancer_diagnosis_id'), 'recurrence', ['cancer_diagnosis_id'], unique=False)
    op.create_index(op.f('ix_recurrence_deleted_by_user_id'), 'recurrence', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_recurrence_entered_by_user_id'), 'recurrence', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_recurrence_evidence_document_id'), 'recurrence', ['evidence_document_id'], unique=False)
    op.create_index(op.f('ix_recurrence_new_cancer_diagnosis_id'), 'recurrence', ['new_cancer_diagnosis_id'], unique=False)
    op.create_index(op.f('ix_recurrence_practice_id'), 'recurrence', ['practice_id'], unique=False)
    op.create_index(op.f('ix_recurrence_source_document_id'), 'recurrence', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_recurrence_source_fact_id'), 'recurrence', ['source_fact_id'], unique=False)
    op.create_table('response_assessment',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('practice_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('cancer_diagnosis_id', sa.UUID(), nullable=True),
    sa.Column('assessed_on', sa.Date(), nullable=False),
    sa.Column('direction', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('imaging_study_id', sa.UUID(), nullable=True),
    sa.Column('overrides_id', sa.UUID(), nullable=True),
    sa.Column('source_fact_id', sa.UUID(), nullable=True),
    sa.Column('source_document_id', sa.UUID(), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_user_id', sa.UUID(), nullable=True),
    sa.Column('deleted_reason', sa.Text(), nullable=True),
    sa.CheckConstraint("direction IN ('responding', 'stable', 'progressing')", name=op.f('ck_response_assessment_direction_allowed')),
    sa.CheckConstraint("overrides_id IS NULL OR source = 'clinician'", name=op.f('ck_response_assessment_override_by_clinician')),
    sa.CheckConstraint("source IN ('radiology_report', 'clinician')", name=op.f('ck_response_assessment_source_allowed')),
    sa.CheckConstraint('(deleted_at IS NULL AND deleted_by_user_id IS NULL AND deleted_reason IS NULL) OR (deleted_at IS NOT NULL AND deleted_by_user_id IS NOT NULL AND length(btrim(deleted_reason)) > 0)', name=op.f('ck_response_assessment_soft_delete')),
    sa.CheckConstraint('source_fact_id IS NOT NULL OR entered_by_user_id IS NOT NULL', name=op.f('ck_response_assessment_provenance')),
    sa.ForeignKeyConstraint(['cancer_diagnosis_id', 'practice_id'], ['cancer_diagnosis.id', 'cancer_diagnosis.practice_id'], name=op.f('fk_response_assessment_cancer_diagnosis_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['entered_by_user_id', 'practice_id'], ['user.id', 'user.practice_id'], name=op.f('fk_response_assessment_entered_by_user_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['imaging_study_id', 'practice_id'], ['imaging_study.id', 'imaging_study.practice_id'], name=op.f('fk_response_assessment_imaging_study_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['overrides_id', 'practice_id'], ['response_assessment.id', 'response_assessment.practice_id'], name=op.f('fk_response_assessment_overrides_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id', 'practice_id'], ['patient.id', 'patient.practice_id'], name=op.f('fk_response_assessment_patient_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['practice_id'], ['practice.id'], name=op.f('fk_response_assessment_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id', 'practice_id'], ['document.id', 'document.practice_id'], name=op.f('fk_response_assessment_source_document_id_practice_id'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_fact_id', 'practice_id'], ['extracted_fact.id', 'extracted_fact.practice_id'], name=op.f('fk_response_assessment_source_fact_id_practice_id'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_response_assessment')),
    sa.UniqueConstraint('id', 'practice_id', name=op.f('uq_response_assessment_id_practice_id'))
    )
    op.create_index(op.f('ix_response_assessment_cancer_diagnosis_id'), 'response_assessment', ['cancer_diagnosis_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_deleted_by_user_id'), 'response_assessment', ['deleted_by_user_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_entered_by_user_id'), 'response_assessment', ['entered_by_user_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_imaging_study_id'), 'response_assessment', ['imaging_study_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_overrides_id'), 'response_assessment', ['overrides_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_patient_id'), 'response_assessment', ['patient_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_practice_id'), 'response_assessment', ['practice_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_source_document_id'), 'response_assessment', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_response_assessment_source_fact_id'), 'response_assessment', ['source_fact_id'], unique=False)
    op.create_foreign_key(op.f('fk_cancer_type_deleted_by_user_id'), 'cancer_type', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_eviq_refresh_log_deleted_by_user_id'), 'eviq_refresh_log', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_treatment_protocol_deleted_by_user_id'), 'treatment_protocol', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_protocol_drug_deleted_by_user_id'), 'protocol_drug', 'user', ['deleted_by_user_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_cns_status_deleted_by_user_id_practice_id'), 'cns_status', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_performance_status_deleted_by_user_id_practice_id'), 'performance_status', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_cancer_diagnosis_deleted_by_user_id_practice_id'), 'cancer_diagnosis', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_biomarker_deleted_by_user_id_practice_id'), 'biomarker', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_oncology_course_detail_deleted_by_user_id_practice_id'), 'oncology_course_detail', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_recurrence_deleted_by_user_id_practice_id'), 'recurrence', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_response_assessment_deleted_by_user_id_practice_id'), 'response_assessment', 'user', ['deleted_by_user_id', 'practice_id'], ['id', 'practice_id'], ondelete='RESTRICT')

    for table in TABLES:
        op.execute(
            f'CREATE TRIGGER set_updated_at BEFORE UPDATE ON "{table}"'
            " FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )
    op.execute('GRANT SELECT ON "eviq_refresh_log" TO vigil_support')
    op.execute(
        "INSERT INTO fact_kind (key, module_key, record_table) VALUES "
        + ", ".join(f"('{kind}', 'oncology', '{kind}')" for kind in ONCOLOGY_FACT_KINDS)
    )
    create_line_of_therapy_rule()


def create_line_of_therapy_rule() -> None:
    """A Line of Therapy only on a systemic, palliative Treatment Course (design doc §6.2).

    It spans treatment_course and oncology_course_detail, so it's a deferred constraint trigger on
    both; it re-reads the committed state, so a course and its detail can change in one transaction.
    """
    op.execute(
        """
        CREATE FUNCTION oncology_check_line_of_therapy() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            course_id uuid;
        BEGIN
            IF TG_TABLE_NAME = 'treatment_course' THEN
                course_id := NEW.id;
            ELSE
                course_id := NEW.treatment_course_id;
            END IF;
            IF EXISTS (
                SELECT 1
                FROM oncology_course_detail d
                JOIN treatment_course c ON c.id = d.treatment_course_id
                WHERE d.treatment_course_id = course_id
                  AND d.line_of_therapy IS NOT NULL
                  AND NOT (c.modality = 'systemic' AND c.intent IS NOT DISTINCT FROM 'palliative')
            ) THEN
                RAISE EXCEPTION 'A Line of Therapy is allowed only on a systemic Treatment Course with palliative intent'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NULL;
        END $$
        """
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER line_of_therapy_rule"
        " AFTER INSERT OR UPDATE ON oncology_course_detail DEFERRABLE INITIALLY DEFERRED"
        " FOR EACH ROW EXECUTE FUNCTION oncology_check_line_of_therapy()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER oncology_line_of_therapy_rule"
        " AFTER UPDATE OF modality, intent ON treatment_course DEFERRABLE INITIALLY DEFERRED"
        " FOR EACH ROW EXECUTE FUNCTION oncology_check_line_of_therapy()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER oncology_line_of_therapy_rule ON treatment_course")
    op.drop_constraint('fk_cancer_type_deleted_by_user_id', 'cancer_type', type_='foreignkey')
    op.drop_constraint('fk_eviq_refresh_log_deleted_by_user_id', 'eviq_refresh_log', type_='foreignkey')
    op.drop_constraint('fk_treatment_protocol_deleted_by_user_id', 'treatment_protocol', type_='foreignkey')
    op.drop_constraint('fk_protocol_drug_deleted_by_user_id', 'protocol_drug', type_='foreignkey')
    op.drop_constraint('fk_cns_status_deleted_by_user_id_practice_id', 'cns_status', type_='foreignkey')
    op.drop_constraint('fk_performance_status_deleted_by_user_id_practice_id', 'performance_status', type_='foreignkey')
    op.drop_constraint('fk_cancer_diagnosis_deleted_by_user_id_practice_id', 'cancer_diagnosis', type_='foreignkey')
    op.drop_constraint('fk_biomarker_deleted_by_user_id_practice_id', 'biomarker', type_='foreignkey')
    op.drop_constraint('fk_oncology_course_detail_deleted_by_user_id_practice_id', 'oncology_course_detail', type_='foreignkey')
    op.drop_constraint('fk_recurrence_deleted_by_user_id_practice_id', 'recurrence', type_='foreignkey')
    op.drop_constraint('fk_response_assessment_deleted_by_user_id_practice_id', 'response_assessment', type_='foreignkey')
    op.drop_index(op.f('ix_response_assessment_source_fact_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_source_document_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_practice_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_patient_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_overrides_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_imaging_study_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_entered_by_user_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_deleted_by_user_id'), table_name='response_assessment')
    op.drop_index(op.f('ix_response_assessment_cancer_diagnosis_id'), table_name='response_assessment')
    op.drop_table('response_assessment')
    op.drop_index(op.f('ix_recurrence_source_fact_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_source_document_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_practice_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_new_cancer_diagnosis_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_evidence_document_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_entered_by_user_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_deleted_by_user_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_cancer_diagnosis_id'), table_name='recurrence')
    op.drop_index(op.f('ix_recurrence_attributed_by_user_id'), table_name='recurrence')
    op.drop_table('recurrence')
    op.drop_index(op.f('ix_oncology_course_detail_treatment_protocol_id'), table_name='oncology_course_detail')
    op.drop_index(op.f('ix_oncology_course_detail_source_fact_id'), table_name='oncology_course_detail')
    op.drop_index(op.f('ix_oncology_course_detail_source_document_id'), table_name='oncology_course_detail')
    op.drop_index(op.f('ix_oncology_course_detail_practice_id'), table_name='oncology_course_detail')
    op.drop_index(op.f('ix_oncology_course_detail_entered_by_user_id'), table_name='oncology_course_detail')
    op.drop_index(op.f('ix_oncology_course_detail_deleted_by_user_id'), table_name='oncology_course_detail')
    op.drop_table('oncology_course_detail')
    op.drop_index(op.f('ix_biomarker_source_fact_id'), table_name='biomarker')
    op.drop_index(op.f('ix_biomarker_source_document_id'), table_name='biomarker')
    op.drop_index(op.f('ix_biomarker_practice_id'), table_name='biomarker')
    op.drop_index('ix_biomarker_latest', table_name='biomarker')
    op.drop_index(op.f('ix_biomarker_entered_by_user_id'), table_name='biomarker')
    op.drop_index(op.f('ix_biomarker_deleted_by_user_id'), table_name='biomarker')
    op.drop_index(op.f('ix_biomarker_cancer_diagnosis_id'), table_name='biomarker')
    op.drop_table('biomarker')
    op.drop_index(op.f('ix_cancer_diagnosis_source_fact_id'), table_name='cancer_diagnosis')
    op.drop_index(op.f('ix_cancer_diagnosis_source_document_id'), table_name='cancer_diagnosis')
    op.drop_index(op.f('ix_cancer_diagnosis_practice_id'), table_name='cancer_diagnosis')
    op.drop_index(op.f('ix_cancer_diagnosis_entered_by_user_id'), table_name='cancer_diagnosis')
    op.drop_index(op.f('ix_cancer_diagnosis_deleted_by_user_id'), table_name='cancer_diagnosis')
    op.drop_index(op.f('ix_cancer_diagnosis_cancer_type_id'), table_name='cancer_diagnosis')
    op.drop_table('cancer_diagnosis')
    op.drop_index(op.f('ix_performance_status_source_fact_id'), table_name='performance_status')
    op.drop_index(op.f('ix_performance_status_source_document_id'), table_name='performance_status')
    op.drop_index(op.f('ix_performance_status_practice_id'), table_name='performance_status')
    op.drop_index(op.f('ix_performance_status_patient_id'), table_name='performance_status')
    op.drop_index(op.f('ix_performance_status_entered_by_user_id'), table_name='performance_status')
    op.drop_index(op.f('ix_performance_status_deleted_by_user_id'), table_name='performance_status')
    op.drop_table('performance_status')
    op.drop_index(op.f('ix_cns_status_source_fact_id'), table_name='cns_status')
    op.drop_index(op.f('ix_cns_status_source_document_id'), table_name='cns_status')
    op.drop_index(op.f('ix_cns_status_practice_id'), table_name='cns_status')
    op.drop_index(op.f('ix_cns_status_patient_id'), table_name='cns_status')
    op.drop_index(op.f('ix_cns_status_entered_by_user_id'), table_name='cns_status')
    op.drop_index(op.f('ix_cns_status_deleted_by_user_id'), table_name='cns_status')
    op.drop_table('cns_status')
    op.drop_index(op.f('ix_protocol_drug_treatment_protocol_id'), table_name='protocol_drug')
    op.drop_index(op.f('ix_protocol_drug_pbs_item_id'), table_name='protocol_drug')
    op.drop_index(op.f('ix_protocol_drug_deleted_by_user_id'), table_name='protocol_drug')
    op.drop_table('protocol_drug')
    op.drop_index(op.f('ix_treatment_protocol_deleted_by_user_id'), table_name='treatment_protocol')
    op.drop_index(op.f('ix_treatment_protocol_cancer_type_id'), table_name='treatment_protocol')
    op.drop_table('treatment_protocol')
    op.drop_index(op.f('ix_eviq_refresh_log_deleted_by_user_id'), table_name='eviq_refresh_log')
    op.drop_table('eviq_refresh_log')
    op.drop_index(op.f('ix_cancer_type_deleted_by_user_id'), table_name='cancer_type')
    op.drop_table('cancer_type')

    op.execute("DROP FUNCTION oncology_check_line_of_therapy()")
    op.execute("DELETE FROM fact_kind WHERE module_key = 'oncology'")
    op.execute("DELETE FROM specialty_module WHERE key = 'oncology'")
