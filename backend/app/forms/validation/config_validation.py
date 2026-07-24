import re
from datetime import date
from typing import Any


class ConfigurationValidationError(ValueError):
    """Custom exception raised when field configuration validation fails."""

    pass


# Simple check for ISO 4217 currency codes
ISO_4217_REGEX = re.compile(r"^[A-Z]{3}$")


def validate_field_configuration(field_type: str, config: dict[str, Any]) -> None:
    # Basic check for requiresConfirmation if present
    if "requiresConfirmation" in config:
        if not isinstance(config["requiresConfirmation"], bool):
            raise ConfigurationValidationError("requiresConfirmation must be a boolean")

    if field_type in ("string", "person_name"):
        # Allowed: minLength, maxLength, requiresConfirmation
        allowed_keys = {"minLength", "maxLength", "requiresConfirmation"}
        for k in config:
            if k not in allowed_keys:
                raise ConfigurationValidationError(
                    f"Key '{k}' is not allowed for field type '{field_type}'"
                )

        min_len = config.get("minLength")
        max_len = config.get("maxLength")

        if min_len is not None:
            if not isinstance(min_len, int) or min_len < 0:
                raise ConfigurationValidationError(
                    "minLength must be a non-negative integer"
                )

        if max_len is not None:
            if not isinstance(max_len, int):
                raise ConfigurationValidationError("maxLength must be an integer")
            if min_len is not None and max_len < min_len:
                raise ConfigurationValidationError(
                    "maxLength must be greater than or equal to minLength"
                )

    elif field_type in ("integer", "decimal"):
        # Allowed: minimum, maximum, requiresConfirmation
        allowed_keys = {"minimum", "maximum", "requiresConfirmation"}
        for k in config:
            if k not in allowed_keys:
                raise ConfigurationValidationError(
                    f"Key '{k}' is not allowed for field type '{field_type}'"
                )

        minimum = config.get("minimum")
        maximum = config.get("maximum")

        # In Python, bool is a subclass of int, so we must explicitly reject bool
        if minimum is not None:
            if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
                raise ConfigurationValidationError("minimum must be a numeric value")

        if maximum is not None:
            if isinstance(maximum, bool) or not isinstance(maximum, (int, float)):
                raise ConfigurationValidationError("maximum must be a numeric value")
            if minimum is not None and maximum < minimum:
                raise ConfigurationValidationError(
                    "maximum must be greater than or equal to minimum"
                )

    elif field_type == "money":
        # Allowed: allowedCurrencies, minimum, maximum, requiresConfirmation
        allowed_keys = {
            "allowedCurrencies",
            "minimum",
            "maximum",
            "requiresConfirmation",
        }
        for k in config:
            if k not in allowed_keys:
                raise ConfigurationValidationError(
                    f"Key '{k}' is not allowed for field type '{field_type}'"
                )

        currencies = config.get("allowedCurrencies")
        minimum = config.get("minimum")
        maximum = config.get("maximum")

        if currencies is not None:
            if not isinstance(currencies, list):
                raise ConfigurationValidationError(
                    "allowedCurrencies must be a list of strings"
                )
            for c in currencies:
                if not isinstance(c, str) or not ISO_4217_REGEX.match(c):
                    raise ConfigurationValidationError(
                        f"Currency '{c}' is not a valid ISO 4217 code"
                    )

        if minimum is not None:
            if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
                raise ConfigurationValidationError("minimum must be a numeric value")

        if maximum is not None:
            if isinstance(maximum, bool) or not isinstance(maximum, (int, float)):
                raise ConfigurationValidationError("maximum must be a numeric value")
            if minimum is not None and maximum < minimum:
                raise ConfigurationValidationError(
                    "maximum must be greater than or equal to minimum"
                )

    elif field_type == "date":
        # Allowed: minimumDate, maximumDate, requiresConfirmation
        allowed_keys = {"minimumDate", "maximumDate", "requiresConfirmation"}
        for k in config:
            if k not in allowed_keys:
                raise ConfigurationValidationError(
                    f"Key '{k}' is not allowed for field type '{field_type}'"
                )

        min_date_str = config.get("minimumDate")
        max_date_str = config.get("maximumDate")

        min_date = None
        max_date = None

        if min_date_str is not None:
            if not isinstance(min_date_str, str):
                raise ConfigurationValidationError(
                    "minimumDate must be an ISO 8601 date string"
                )
            try:
                min_date = date.fromisoformat(min_date_str)
            except ValueError as e:
                raise ConfigurationValidationError(
                    f"minimumDate '{min_date_str}' is not a valid ISO 8601 date"
                ) from e

        if max_date_str is not None:
            if not isinstance(max_date_str, str):
                raise ConfigurationValidationError(
                    "maximumDate must be an ISO 8601 date string"
                )
            try:
                max_date = date.fromisoformat(max_date_str)
            except ValueError as e:
                raise ConfigurationValidationError(
                    f"maximumDate '{max_date_str}' is not a valid ISO 8601 date"
                ) from e

        if min_date is not None and max_date is not None:
            if max_date < min_date:
                raise ConfigurationValidationError(
                    "maximumDate must not be earlier than minimumDate"
                )

    elif field_type in ("single_choice", "multiple_choice"):
        # Allowed: requiresConfirmation
        allowed_keys = {"requiresConfirmation"}
        for k in config:
            if k not in allowed_keys:
                raise ConfigurationValidationError(
                    f"Key '{k}' is not allowed for field type '{field_type}'"
                )

    else:
        # For other non-choice field types (email, phone, address, country,
        # multiline_text, boolean)
        # We only allow requiresConfirmation
        allowed_keys = {"requiresConfirmation"}
        for k in config:
            if k not in allowed_keys:
                raise ConfigurationValidationError(
                    f"Key '{k}' is not allowed for field type '{field_type}'"
                )
