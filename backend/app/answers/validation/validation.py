import re
from datetime import datetime
from typing import Any

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^\+?[\d\s\-]{5,25}$")
ISO_COUNTRY_REGEX = re.compile(r"^[A-Z]{2}$")


def validate_value(
    field_type: str,
    val: Any,
    required: bool,
    config: dict[str, Any],
    options: list[Any] | None = None,
) -> tuple[bool, str | None]:
    """Deterministically validates a normalized value against configuration.

    Checks value type, requirements, and custom configurations.
    """
    # 1. Required check
    is_empty = False
    if val is None:
        is_empty = True
    elif isinstance(val, str) and not val.strip():
        is_empty = True
    elif isinstance(val, list) and not val:
        is_empty = True
    elif isinstance(val, dict):
        if field_type == "person_name":
            is_empty = not val.get("fullName")
        elif field_type == "money":
            is_empty = val.get("amount") is None
        else:
            is_empty = not val

    if is_empty:
        if required:
            return False, "Field is required."
        return True, None

    # If it is empty but not required, it is valid
    if is_empty:
        return True, None

    # 2. Field-type specific checks
    if field_type in ("string", "multiline_text"):
        if not isinstance(val, str):
            return False, "Value must be a string."
        min_len = config.get("minLength")
        max_len = config.get("maxLength")
        if min_len is not None and len(val) < min_len:
            return False, f"Value must be at least {min_len} characters long."
        if max_len is not None and len(val) > max_len:
            return False, f"Value must be at most {max_len} characters long."

    elif field_type == "person_name":
        if not isinstance(val, dict) or "fullName" not in val:
            return (
                False,
                "Value must be a person name dictionary containing 'fullName'.",
            )
        name = val["fullName"]
        if not isinstance(name, str) or not name.strip():
            return False, "Full name must be a non-empty string."
        max_len = config.get("maxLength")
        if max_len is not None and len(name) > max_len:
            return False, f"Full name must be at most {max_len} characters long."

    elif field_type == "email":
        if not isinstance(val, str):
            return False, "Value must be a string."
        if not EMAIL_REGEX.match(val):
            return False, "Invalid email address syntax."

    elif field_type == "date":
        if not isinstance(val, str):
            return False, "Value must be a string."
        try:
            parsed_date = datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return False, "Invalid date format. Expected YYYY-MM-DD."

        min_date_str = config.get("minimumDate")
        max_date_str = config.get("maximumDate")
        if min_date_str:
            try:
                min_date = datetime.strptime(min_date_str, "%Y-%m-%d").date()
                if parsed_date < min_date:
                    return False, f"Date must be on or after {min_date_str}."
            except ValueError:
                pass
        if max_date_str:
            try:
                max_date = datetime.strptime(max_date_str, "%Y-%m-%d").date()
                if parsed_date > max_date:
                    return False, f"Date must be on or before {max_date_str}."
            except ValueError:
                pass

    elif field_type in ("integer", "decimal", "number"):
        if (
            isinstance(val, bool)
            or not isinstance(val, (int, float))
            or (field_type == "integer" and not isinstance(val, int))
        ):
            return (
                False,
                f"Value must be an {field_type}.",
            )
        min_val = config.get("minimum")
        max_val = config.get("maximum")
        if min_val is not None and val < min_val:
            return False, f"Value must be at least {min_val}."
        if max_val is not None and val > max_val:
            return False, f"Value must be at most {max_val}."

    elif field_type == "money":
        if not isinstance(val, dict):
            return False, "Value must be a dictionary representing money."
        amount = val.get("amount")
        currency = val.get("currency")
        period = val.get("period")

        if amount is None or not isinstance(amount, (int, float)):
            return False, "Money amount must be a number."
        if not currency or not isinstance(currency, str) or len(currency) != 3:
            return False, "Money currency code must be a 3-letter ISO code."
        if not period or not isinstance(period, str):
            return False, "Money period must be a string."

        min_val = config.get("minimum")
        max_val = config.get("maximum")
        if min_val is not None and amount < min_val:
            return False, f"Amount must be at least {min_val}."
        if max_val is not None and amount > max_val:
            return False, f"Amount must be at most {max_val}."

    elif field_type == "boolean":
        if not isinstance(val, bool):
            return False, "Value must be a boolean."

    elif field_type in ("single_choice", "choice"):
        opt_values = set()
        if options:
            opt_values = {opt.value for opt in options}
        else:
            opt_opts = config.get("options", [])
            opt_values = {opt["value"] for opt in opt_opts if "value" in opt}
        if opt_values and val not in opt_values:
            return False, f"Value '{val}' must be one of the canonical options."

    elif field_type == "multiple_choice":
        if not isinstance(val, list):
            return False, "Value must be a list."
        opt_values = set()
        if options:
            opt_values = {opt.value for opt in options}
        else:
            opt_opts = config.get("options", [])
            opt_values = {opt["value"] for opt in opt_opts if "value" in opt}
        for item in val:
            if item not in opt_values:
                return (
                    False,
                    f"Option value '{item}' must be one of the canonical options.",
                )

    elif field_type == "country":
        if not isinstance(val, str):
            return False, "Value must be a string."
        if not ISO_COUNTRY_REGEX.match(val):
            return False, "Country code must be a valid 2-letter uppercase ISO code."

    elif field_type == "phone":
        if not isinstance(val, str):
            return False, "Value must be a string."
        if not PHONE_REGEX.match(val):
            return False, "Invalid phone number format."

    elif field_type == "address":
        # Address validation in Phase 4:
        # Accept structured dictionary or non-empty string.
        if not isinstance(val, (dict, str)):
            return False, "Address must be a string or a structured object."
        if isinstance(val, dict):
            # At least one recognisable address part. Demanding both a street
            # *and* a city rejected perfectly good answers: a "postal code,
            # city" field has no street, so "70188, Stuttgart" was reported
            # invalid. An address with no identifiable part at all is still
            # rejected.
            recognised = any(
                val.get(part)
                for part in ("street", "city", "postal_code", "postalCode", "zip")
            )
            if not recognised:
                return (
                    False,
                    "Enter an address, for example: Hauptstraße 1, 70188 Stuttgart.",
                )

    return True, None
