"""Edits sent as "only the fields that changed": what actually changed, for one Verification's before/after."""

from collections.abc import Collection, Mapping
from typing import Any, Literal

from pydantic import BaseModel


def blank_to_none(values: Mapping[str, Any]) -> dict[str, Any]:
    """Empty text means "not given" (or, in an edit, "clear it")."""
    return {field: (value or None) if isinstance(value, str) else value for field, value in values.items()}


def changed_fields(
    current: Mapping[str, Any], change: BaseModel, required: Collection[str] = (), mode: Literal["python", "json"] = "python"
) -> dict[str, Any]:
    """The fields sent that differ from `current`. A required field sent empty is ignored, never cleared.

    `mode="json"` compares (and returns) dates as ISO text, ready for a Verification's before/after."""
    requested = blank_to_none(change.model_dump(exclude_unset=True, mode=mode))
    return {
        field: value
        for field, value in requested.items()
        if value != current[field] and not (value is None and field in required)
    }
