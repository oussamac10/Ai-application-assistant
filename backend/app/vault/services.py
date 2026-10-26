from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.answers.models import FormAnswer
from app.answers.normalization.context import format_money_output
from app.answers.normalization.normalization import normalize_value
from app.answers.repositories import AnswerRepository
from app.answers.validation.validation import validate_value
from app.forms.models import FormField
from app.forms.repositories import FormRepository
from app.sessions.services import SessionService
from app.vault.crypto import decrypt_vault_payload, encrypt_vault_payload
from app.vault.errors import VaultNotFoundError, VaultValidationError
from app.vault.models import UserProfileEntry
from app.vault.repositories import ProfileVaultRepository

_QUESTION_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,99}$")
_ISO_LANG_RE = re.compile(r"^[a-z]{2}$")
_IBAN_CLEAN_RE = re.compile(r"\s+")
_IBAN_FORMAT_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")

# Reusable vault field types (never signatures, declarations, or form-specific choice enums)
_SUPPORTED_VAULT_FIELD_TYPES = frozenset(
    {
        "string",
        "text",
        "multiline_text",
        "person_name",
        "email",
        "date",
        "phone",
        "address",
        "country",
        "iban",
        "integer",
        "decimal",
    }
)

# Deterministic alias table mapping both canonical semantic keys and common
# predefined/detected field keys onto canonical Profile Vault keys.
_SEMANTIC_KEY_ALIASES: dict[str, str] = {
    "personal.first_name": "personal.first_name",
    "person.first_name": "personal.first_name",
    "first_name": "personal.first_name",
    "vorname": "personal.first_name",
    "prenom": "personal.first_name",
    "personal.last_name": "personal.last_name",
    "person.last_name": "personal.last_name",
    "last_name": "personal.last_name",
    "surname": "personal.last_name",
    "family_name": "personal.last_name",
    "nachname": "personal.last_name",
    "familienname": "personal.last_name",
    "nom": "personal.last_name",
    "personal.full_name": "personal.full_name",
    "person.full_name": "personal.full_name",
    "full_name": "personal.full_name",
    "applicant_name": "personal.full_name",
    "person.date_of_birth": "person.date_of_birth",
    "personal.date_of_birth": "person.date_of_birth",
    "date_of_birth": "person.date_of_birth",
    "birth_date": "person.date_of_birth",
    "geburtsdatum": "person.date_of_birth",
    "date_de_naissance": "person.date_of_birth",
    "personal.place_of_birth": "personal.place_of_birth",
    "person.place_of_birth": "personal.place_of_birth",
    "place_of_birth": "personal.place_of_birth",
    "birth_place": "personal.place_of_birth",
    "geburtsort": "personal.place_of_birth",
    "personal.nationality": "personal.nationality",
    "person.nationality": "personal.nationality",
    "nationality": "personal.nationality",
    "staatsangehoerigkeit": "personal.nationality",
    "contact.email": "contact.email",
    "email": "contact.email",
    "email_address": "contact.email",
    "e_mail": "contact.email",
    "e_mail_adresse": "contact.email",
    "contact.phone": "contact.phone",
    "phone": "contact.phone",
    "phone_number": "contact.phone",
    "telefon": "contact.phone",
    "telefonnummer": "contact.phone",
    "address.street": "address.street",
    "street": "address.street",
    "strasse": "address.street",
    "address.house_number": "address.house_number",
    "house_number": "address.house_number",
    "hausnummer": "address.house_number",
    "address.postal_code": "address.postal_code",
    "postal_code": "address.postal_code",
    "postleitzahl": "address.postal_code",
    "plz": "address.postal_code",
    "zip_code": "address.postal_code",
    "address.city": "address.city",
    "city": "address.city",
    "wohnort": "address.city",
    "ort": "address.city",
    "stadt": "address.city",
    "address.country": "address.country",
    "country": "address.country",
    "land": "address.country",
    "address.full_address": "address.full_address",
    "current_address": "address.full_address",
    "address": "address.full_address",
    "anschrift": "address.full_address",
    "aktuelle_anschrift": "address.full_address",
    "adresse": "address.full_address",
    "residence.move_in_date": "residence.move_in_date",
    "move_in_date": "residence.move_in_date",
    "einzugsdatum": "residence.move_in_date",
    "finance.iban": "finance.iban",
    "iban": "finance.iban",
}


def canonicalize_vault_key(raw_key: str | None) -> str | None:
    if not raw_key:
        return None
    cleaned = raw_key.strip().lower()
    if not cleaned:
        return None
    if cleaned in _SEMANTIC_KEY_ALIASES:
        return _SEMANTIC_KEY_ALIASES[cleaned]
    # Strip trailing numeric deduplication suffix if not a repeated row key
    if "." in cleaned and _QUESTION_KEY_RE.match(cleaned):
        return cleaned
    return _SEMANTIC_KEY_ALIASES.get(cleaned)


def resolve_field_vault_key(field: FormField) -> str | None:
    """Resolves a FormField to a canonical Profile Vault key if reusable."""
    if field.question_key:
        mapped = canonicalize_vault_key(field.question_key)
        if mapped:
            return mapped
    return canonicalize_vault_key(field.key)


def _is_valid_iban(raw_iban: str) -> bool:
    compact = _IBAN_CLEAN_RE.sub("", raw_iban.strip().upper())
    if not _IBAN_FORMAT_RE.match(compact):
        return False
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(ord(ch) - 55) if "A" <= ch <= "Z" else ch for ch in rearranged)
    try:
        return int(digits) % 97 == 1
    except ValueError:
        return False


def _normalize_and_validate_vault_input(
    question_key: str, field_type: str, value: str
) -> tuple[str, Any]:
    ft = field_type.strip().lower()
    if ft not in _SUPPORTED_VAULT_FIELD_TYPES:
        raise VaultValidationError(
            f"Field type '{field_type}' cannot be stored in the Profile Vault.",
            "unsupported_vault_field_type",
        )
    cleaned_val = value.strip()
    if not cleaned_val:
        raise VaultValidationError(
            "Profile Vault value must not be empty.", "invalid_vault_value"
        )

    effective_ft = "string" if ft == "text" else ft
    if effective_ft == "iban" or question_key == "finance.iban":
        compact_iban = _IBAN_CLEAN_RE.sub("", cleaned_val.upper())
        if not _is_valid_iban(compact_iban):
            raise VaultValidationError(
                "Invalid IBAN checksum or format.", "invalid_vault_value"
            )
        return "iban", compact_iban

    norm_val = normalize_value(effective_ft, cleaned_val)
    is_valid, err_msg = validate_value(effective_ft, norm_val, required=True, config={})
    if not is_valid:
        raise VaultValidationError(
            err_msg or "Invalid value for field type.", "invalid_vault_value"
        )
    return effective_ft, norm_val


def _format_output_for_field(field_type: str, norm_val: Any, raw_value: str) -> str:
    if field_type == "person_name" and isinstance(norm_val, dict):
        return str(norm_val.get("fullName", raw_value)).strip()
    if field_type == "money" and isinstance(norm_val, dict):
        return format_money_output(norm_val)
    if isinstance(norm_val, str):
        return norm_val
    return str(norm_val) if norm_val is not None else raw_value


class ProfileVaultService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProfileVaultRepository(db)
        self.session_service = SessionService(db)
        self.form_repo = FormRepository(db)
        self.answer_repo = AnswerRepository(db)

    @staticmethod
    def _deserialize_entry(entry: UserProfileEntry) -> dict[str, Any]:
        decrypted = decrypt_vault_payload(entry.encrypted_payload)
        return {
            "question_key": entry.question_key,
            "field_type": entry.field_type,
            "value": str(decrypted.get("value", "")),
            "normalized_value": decrypted.get("normalized_value"),
            "value_language": entry.value_language,
            "updated_at": entry.updated_at,
        }

    def list_entries(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.repo.list_for_user(user_id)
        return [self._deserialize_entry(r) for r in rows]

    def export_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [
            {
                "question_key": item["question_key"],
                "field_type": item["field_type"],
                "value": item["value"],
                "value_language": item["value_language"],
                "updated_at": item["updated_at"],
            }
            for item in self.list_entries(user_id)
        ]

    def upsert_entry(
        self,
        user_id: str,
        question_key: str,
        value: str,
        field_type: str = "string",
        value_language: str = "en",
    ) -> dict[str, Any]:
        raw_key = question_key.strip().lower()
        canonical_key = canonicalize_vault_key(raw_key) or (
            raw_key if _QUESTION_KEY_RE.match(raw_key) else None
        )
        if not canonical_key or not _QUESTION_KEY_RE.match(canonical_key):
            raise VaultValidationError(
                "Invalid semantic question key.", "invalid_vault_key"
            )
        lang = value_language.strip().lower()
        if not _ISO_LANG_RE.match(lang):
            raise VaultValidationError(
                "Invalid ISO 639-1 language code.", "invalid_language"
            )

        effective_ft, norm_val = _normalize_and_validate_vault_input(
            canonical_key, field_type, value
        )
        ciphertext = encrypt_vault_payload(
            {
                "value": value.strip(),
                "normalized_value": norm_val,
            }
        )
        saved = self.repo.upsert(
            user_id=user_id,
            question_key=canonical_key,
            field_type=effective_ft,
            encrypted_payload=ciphertext,
            value_language=lang,
        )
        return self._deserialize_entry(saved)

    def delete_entry(self, user_id: str, question_key: str) -> None:
        raw_key = question_key.strip().lower()
        canonical_key = canonicalize_vault_key(raw_key) or raw_key
        if not self.repo.delete_key(user_id, canonical_key):
            raise VaultNotFoundError("Profile Vault entry not found.")

    def clear_vault(self, user_id: str) -> None:
        self.repo.delete_all_for_user(user_id)

    def save_session_answers_to_vault(
        self, user_id: str, session_public_id: str
    ) -> dict[str, Any]:
        """Opt-in save of confirmed reusable answers from an owned session."""
        session = self.session_service.get_session(
            session_public_id, raw_token=None, current_user_id=user_id
        )
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            return {"saved_count": 0, "saved_keys": []}

        answers = {
            a.field_id: a for a in self.answer_repo.get_answers_for_session(session.id)
        }
        saved_keys: list[str] = []
        for field in version.fields:
            if field.field_type not in _SUPPORTED_VAULT_FIELD_TYPES:
                continue
            vault_key = resolve_field_vault_key(field)
            if not vault_key:
                continue
            ans = answers.get(field.id)
            if (
                not ans
                or ans.status != "confirmed"
                or not ans.confirmed_by_user
                or not ans.original_answer
                or not ans.original_answer.strip()
            ):
                continue

            try:
                self.upsert_entry(
                    user_id=user_id,
                    question_key=vault_key,
                    value=ans.original_answer.strip(),
                    field_type=field.field_type,
                    value_language=ans.original_language or session.user_language,
                )
                saved_keys.append(vault_key)
            except VaultValidationError:
                continue

        return {"saved_count": len(saved_keys), "saved_keys": saved_keys}

    def prefill_session_from_vault(
        self, user_id: str, session_public_id: str
    ) -> dict[str, Any]:
        """Populates unanswered matching session fields from the user's Profile Vault.

        Invariants (`AGENTS.md` Section 1 & `multilingual-form-engine`):
        - Never overwrites already answered, skipped, or confirmed fields.
        - Always sets `status = "awaiting_confirmation"` (`confirmed_by_user = False`)
          so the applicant explicitly reviews and confirms every pre-filled answer.
        - Never performs silent cross-script personal name transliteration.
        """
        session = self.session_service.get_session(
            session_public_id, raw_token=None, current_user_id=user_id
        )
        version = self.form_repo.get_version(session.form_version_id)
        if not version:
            return {"prefilled_count": 0, "prefilled_field_keys": []}

        vault_by_key = {
            item["question_key"]: item for item in self.list_entries(user_id)
        }
        if not vault_by_key:
            return {"prefilled_count": 0, "prefilled_field_keys": []}

        existing_answers = {
            a.field_id: a for a in self.answer_repo.get_answers_for_session(session.id)
        }
        prefilled_field_keys: list[str] = []

        for field in sorted(version.fields, key=lambda f: f.position):
            if field.field_type not in _SUPPORTED_VAULT_FIELD_TYPES:
                continue
            existing = existing_answers.get(field.id)
            if existing is not None and existing.status != "unanswered":
                continue

            vault_key = resolve_field_vault_key(field)
            if not vault_key or vault_key not in vault_by_key:
                continue

            vault_item = vault_by_key[vault_key]
            raw_value = str(vault_item["value"]).strip()
            if not raw_value:
                continue

            norm_val = normalize_value(field.field_type, raw_value)
            is_valid, _ = validate_value(
                field.field_type,
                norm_val,
                field.required,
                field.configuration or {},
                options=field.options,
            )
            if not is_valid:
                continue

            output_val = _format_output_for_field(field.field_type, norm_val, raw_value)
            if existing is not None:
                existing.original_answer = raw_value
                existing.original_language = str(
                    vault_item.get("value_language") or session.user_language
                )
                existing.normalized_value = norm_val
                existing.output_value = output_val
                existing.status = "awaiting_confirmation"
                existing.validation_status = "valid"
                existing.translation_status = "not_required"
                existing.requires_clarification = False
                existing.confirmed_by_user = False
                existing.confirmed_at = None
            else:
                self.db.add(
                    FormAnswer(
                        session_id=session.id,
                        field_id=field.id,
                        original_answer=raw_value,
                        original_language=str(
                            vault_item.get("value_language") or session.user_language
                        ),
                        normalized_value=norm_val,
                        output_value=output_val,
                        status="awaiting_confirmation",
                        validation_status="valid",
                        translation_status="not_required",
                        requires_clarification=False,
                        confirmed_by_user=False,
                        confirmed_at=None,
                    )
                )
            prefilled_field_keys.append(field.key)

        if prefilled_field_keys:
            self.db.commit()

        return {
            "prefilled_count": len(prefilled_field_keys),
            "prefilled_field_keys": prefilled_field_keys,
        }
