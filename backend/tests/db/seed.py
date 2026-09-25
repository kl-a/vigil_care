"""Minimal valid synthetic rows for database tests. Every value is made up."""

import uuid
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb


MEMBERSHIP_FIELDS = ("is_active", "provider_id", "last_login_at")


class Seed:
    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self.conn = conn

    def insert(self, table: str, **values: Any) -> uuid.UUID:
        schema, _, name = table.rpartition(".")
        target = sql.Identifier(schema, name) if schema else sql.Identifier(name)
        columns = list(values)
        params = [Jsonb(v) if isinstance(v, (dict, list)) else v for v in values.values()]
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            target,
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )
        row = self.conn.cursor(row_factory=tuple_row).execute(query, params).fetchone()
        assert row is not None
        return uuid.UUID(str(row[0]))

    # --- Practice, people ----------------------------------------------------------------

    def practice(self) -> uuid.UUID:
        return self.insert("practice", name="Synthetic Oncology Practice")

    def user(self, practice_id: uuid.UUID, job_title: str = "clinician", **values: Any) -> uuid.UUID:
        """A login with a Practice Membership at `practice_id`. Membership columns go to the Membership."""
        membership = {field: values.pop(field) for field in MEMBERSHIP_FIELDS if field in values}
        values.setdefault("username", f"user-{uuid.uuid4().hex[:8]}")
        values.setdefault("display_name", "Synthetic User")
        user_id = self.insert("user", password_hash="not-a-real-hash", **values)
        self.member(practice_id, user_id, job_title, **membership)
        return user_id

    def member(self, practice_id: uuid.UUID, user_id: uuid.UUID, job_title: str = "clinician", **values: Any) -> uuid.UUID:
        """An existing login joins another Practice."""
        return self.insert("practice_membership", practice_id=practice_id, user_id=user_id, job_title=job_title, **values)

    def provider(self, practice_id: uuid.UUID, **values: Any) -> uuid.UUID:
        values.setdefault("specialty", "medical_oncology")
        return self.insert(
            "provider", practice_id=practice_id, first_name="Syn", last_name="Thetic", **values
        )

    def patient(self, practice_id: uuid.UUID, **values: Any) -> uuid.UUID:
        values.setdefault("pseudonym", f"VG-{uuid.uuid4().hex[:8]}")
        return self.insert("patient", practice_id=practice_id, **values)

    def everyone(self) -> dict[str, uuid.UUID]:
        """A Practice with a clinician and a Patient: the usual starting point."""
        practice = self.practice()
        return {
            "practice": practice,
            "user": self.user(practice),
            "patient": self.patient(practice),
        }

    # --- Clinical Record ------------------------------------------------------------------

    def condition(self, ids: dict[str, uuid.UUID], **values: Any) -> uuid.UUID:
        return self.insert(
            "condition",
            practice_id=ids["practice"],
            patient_id=ids["patient"],
            name="Synthetic condition",
            entered_by_user_id=ids["user"],
            **values,
        )

    def treatment_course(
        self, ids: dict[str, uuid.UUID], modality: str = "systemic", intent: str | None = "palliative"
    ) -> uuid.UUID:
        return self.insert(
            "treatment_course",
            practice_id=ids["practice"],
            condition_id=self.condition(ids),
            modality=modality,
            intent=intent,
            entered_by_user_id=ids["user"],
        )

    def medication(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        return self.insert(
            "medication",
            practice_id=ids["practice"],
            patient_id=ids["patient"],
            drug_name_raw="synthetic drug",
            source="doctor_entered",
            confidence="high",
            entered_by_user_id=ids["user"],
        )

    # --- Trials & matching ----------------------------------------------------------------

    def trial_snapshot(self) -> uuid.UUID:
        return self.insert("trial_snapshot", taken_at="2026-09-01T00:00:00Z", registry="CTGOV", record_count=1)

    def trial(self) -> uuid.UUID:
        return self.insert(
            "trial", registry="CTGOV", external_id=f"NCT{uuid.uuid4().int % 10**8:08d}", title="Synthetic trial"
        )

    def match_run(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        return self.insert(
            "match_run",
            practice_id=ids["practice"],
            patient_id=ids["patient"],
            target_condition_id=self.condition(ids),
            snapshot_id=self.trial_snapshot(),
            clinical_record_as_of="2026-09-01T00:00:00Z",
            ruleset_version="test",
            run_by_user_id=ids["user"],
        )

    def match_result(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        return self.insert(
            "match_result",
            practice_id=ids["practice"],
            match_run_id=self.match_run(ids),
            trial_id=self.trial(),
            match_state="NEEDS_INFORMATION",
        )

    def criterion_evaluation(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        criterion = self.insert(
            "trial_criterion", trial_id=self.trial(), kind="inclusion", raw_text="ECOG 0-1", scope="whole_person"
        )
        return self.insert(
            "criterion_evaluation",
            practice_id=ids["practice"],
            match_result_id=self.match_result(ids),
            trial_criterion_id=criterion,
            result="UNKNOWN",
        )

    # --- Audit & documents ----------------------------------------------------------------

    def verification(self, ids: dict[str, uuid.UUID], **values: Any) -> uuid.UUID:
        values.setdefault("action", "accept")
        values.setdefault("job_title_at_time", "clinician")
        return self.insert(
            "verification",
            practice_id=ids["practice"],
            subject_table="condition",
            subject_id=uuid.uuid4(),
            user_id=ids["user"],
            **values,
        )

    def medication_change_log(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        return self.insert(
            "medication_change_log",
            practice_id=ids["practice"],
            medication_id=self.medication(ids),
            change_type="added",
            changed_by_user_id=ids["user"],
        )

    def llm_call_log(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        return self.insert(
            "llm_call_log",
            practice_id=ids["practice"],
            pipeline_step="classify",
            endpoint="local_vlm",
            model_id="synthetic-model",
            input_hash="abc123",
        )

    def document(self, ids: dict[str, uuid.UUID], **values: Any) -> uuid.UUID:
        values.setdefault("original_sha256", uuid.uuid4().hex)
        values.setdefault("patient_id", ids["patient"])
        return self.insert(
            "document",
            practice_id=ids["practice"],
            original_uri="file:///synthetic.pdf",
            uploaded_by_user_id=ids["user"],
            input_method="native_pdf",
            **values,
        )

    def cloud_request(self, ids: dict[str, uuid.UUID]) -> uuid.UUID:
        return self.insert(
            "cloud_request",
            practice_id=ids["practice"],
            document_id=self.document(ids),
            purpose="vlm_read",
            payload_kind="masked_image",
            payload_sha256="def456",
            initiated_by_user_id=ids["user"],
            model_id="synthetic-model",
        )
