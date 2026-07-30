"""Errors the answer flow reports to the client.

`confirm_summary` used to raise a single `StateConflictError` carrying a
sentence — "Field 'date_de_d_but_d_emploi' contains invalid value." The client
could do nothing with it: it names one field out of possibly several, does not
say what is wrong, and the wording was wrong anyway (the field was empty, not
invalid). This carries the whole picture as data instead.

Field *keys* only. A key is a stable identifier the client already holds; the
submitted value, the label and any normalized form of either are private and
never leave the service through an error.
"""

from __future__ import annotations

from dataclasses import dataclass

SUMMARY_NOT_CONFIRMABLE = "summary_not_confirmable"


@dataclass(frozen=True)
class FieldProblem:
    """One reason one field is not ready. `reason` is a stable code, never a
    sentence and never a value."""

    field_key: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"field_key": self.field_key, "reason": self.reason}


class SummaryNotConfirmableError(Exception):
    """The summary cannot be confirmed yet, with every blocking field listed.

    Reported as HTTP 409: the request is well formed and authorized, the
    session is simply not in a state where it can be finalized.
    """

    def __init__(
        self,
        missing_required_fields: list[FieldProblem],
        invalid_answer_fields: list[FieldProblem],
    ) -> None:
        self.missing_required_fields = missing_required_fields
        self.invalid_answer_fields = invalid_answer_fields
        super().__init__(
            "The form cannot be confirmed yet: "
            f"{len(missing_required_fields)} required question(s) unanswered, "
            f"{len(invalid_answer_fields)} answer(s) need attention."
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "code": SUMMARY_NOT_CONFIRMABLE,
            "detail": str(self),
            "missing_required_fields": [
                problem.as_dict() for problem in self.missing_required_fields
            ],
            "invalid_answer_fields": [
                problem.as_dict() for problem in self.invalid_answer_fields
            ],
        }
