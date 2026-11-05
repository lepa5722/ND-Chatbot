from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Literal

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
)


def utcnow() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def validate_nonempty(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Value must be a non-empty string.")
    return value.strip()


class Approach(str, Enum):
    """Supported interaction approaches."""

    DA = "DA"
    SRS = "SRS"
    PAS = "PAS"


class MemoryCategory(str, Enum):
    """Supported user-controlled memory categories."""

    PREFERENCES = "preferences"
    PERSONAL_CONTEXT = "personal_context"
    DECISIONS_IN_PROGRESS = "decisions_in_progress"
    SYSTEM_NOTES = "system_notes"


class MemoryEntry(BaseModel):
    """
    Represents a session-scoped memory entry.

    Demographic and clinical fields are intentionally excluded.
    Unknown fields are rejected.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    category: MemoryCategory
    content: str

    created_at: str = Field(default_factory=utcnow)
    last_used_at: Optional[str] = None

    consent_basis: str
    status: Literal["active", "deleted"] = "active"

    @field_validator("id", "content", "consent_basis")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        return validate_nonempty(value)


class ChatRequest(BaseModel):
    """Incoming user chat request."""

    model_config = ConfigDict(extra="forbid")

    message: str
    session_id: str = "default"
    scenario_id: Optional[str] = None

    @field_validator("message", "session_id")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        return validate_nonempty(value)

    @field_validator("scenario_id")
    @classmethod
    def validate_optional_scenario_id(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is not None:
            return validate_nonempty(value)
        return value


class AdaptationProposalIn(BaseModel):
    """Input for an adaptation proposal."""

    model_config = ConfigDict(extra="forbid")

    signal_type: str
    signal_value: str
    session_id: str = "default"
    scenario_id: Optional[str] = None

    @field_validator("signal_type", "signal_value", "session_id")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        return validate_nonempty(value)

    @field_validator("scenario_id")
    @classmethod
    def validate_optional_scenario_id(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is not None:
            return validate_nonempty(value)
        return value


class AdaptationDecisionIn(BaseModel):
    """User's response to an adaptation proposal."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["accepted", "refused", "deferred"]
    session_id: str = "default"

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        return validate_nonempty(value)
