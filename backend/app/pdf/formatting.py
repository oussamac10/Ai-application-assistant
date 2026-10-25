import json
from typing import Any


def format_field_value(
    *,
    field_type: str,
    normalized_value: Any,
    output_value: str | None,
    output_language: str,
) -> str:
    """
    Deterministically format field values based on type, normalized value,
    output value, and output language.
    """
    # 1. Date formatting
    if field_type == "date":
        # Canonical is YYYY-MM-DD
        val = normalized_value or output_value
        if isinstance(val, str) and len(val) == 10 and val[4] == "-" and val[7] == "-":
            year, month, day = val.split("-")
            # Format based on output language
            if output_language == "de":
                return f"{day}.{month}.{year}"
            elif output_language == "fr":
                return f"{day}/{month}/{year}"
            else:
                return f"{day}/{month}/{year}"  # Default to DD/MM/YYYY
        return str(val) if val is not None else ""

    # 2. Boolean formatting
    if field_type == "boolean":
        val = normalized_value
        if val is None and output_value:
            val = output_value.lower() in ("true", "yes", "1")
        if isinstance(val, str):
            val = val.lower() in ("true", "yes", "1")

        if val is True:
            return (
                "Ja"
                if output_language == "de"
                else "Oui"
                if output_language == "fr"
                else "نعم"
                if output_language == "ar"
                else "Yes"
            )
        elif val is False:
            return (
                "Nein"
                if output_language == "de"
                else "Non"
                if output_language == "fr"
                else "لا"
                if output_language == "ar"
                else "No"
            )
        return ""

    # 3. Multiple Choice formatting
    if field_type == "multiple_choice":
        val = normalized_value
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                pass
        if isinstance(val, list):
            return ", ".join(str(item).capitalize() for item in val)
        return output_value or str(val) if val is not None else ""

    # 4. Money formatting
    if field_type == "money":
        val = normalized_value
        if isinstance(val, dict):
            amount = val.get("amount", "")
            currency = val.get("currency", "")
            period = val.get("period", "")
            parts = []
            if amount != "":
                # Format decimal nicely
                try:
                    amt_float = float(amount)
                    if amt_float.is_integer():
                        parts.append(f"{int(amt_float):,}")
                    else:
                        parts.append(f"{amt_float:,.2f}")
                except Exception:
                    parts.append(str(amount))
            if currency:
                parts.append(str(currency))
            if period and str(period).strip().lower() != "once":
                parts.append(str(period))
            return " ".join(parts)
        return output_value or str(val) if val is not None else ""

    # 5. Address formatting
    if field_type == "address":
        val = normalized_value
        if isinstance(val, dict):
            street = val.get("street", "")
            postal_code = val.get("postal_code", "")
            city = val.get("city", "")
            country = val.get("country", "")
            parts = [street, f"{postal_code} {city}", country]
            return ", ".join(p for p in parts if p.strip())
        return output_value or str(val) if val is not None else ""

    # Fallback to output_value, then normalized_value
    if output_value is not None:
        return str(output_value)
    if normalized_value is not None:
        return str(normalized_value)
    return ""
