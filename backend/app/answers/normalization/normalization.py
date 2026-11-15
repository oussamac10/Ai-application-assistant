import json
import re
from datetime import datetime
from typing import Any


def normalize_value(field_type: str, raw_val: Any) -> Any:
    """Normalize user input based on the field type into a canonical representation."""
    if raw_val is None:
        return None

    if field_type == "boolean":
        if isinstance(raw_val, bool):
            return raw_val
        val_str = str(raw_val).strip().lower()
        if val_str in ("true", "1", "yes", "y", "oui", "ja", "نعم"):
            return True
        if val_str in ("false", "0", "no", "n", "non", "nein", "لا"):
            return False
        return raw_val

    elif field_type == "country":
        from app.answers.normalization.countries import normalize_country_value

        return normalize_country_value(raw_val)

    elif field_type == "multiple_choice":
        if not isinstance(raw_val, list):
            if isinstance(raw_val, str):
                # A provider may hand back the raw JSON-array string
                # unparsed; fall back to CSV only if it isn't one.
                try:
                    parsed = json.loads(raw_val)
                except (ValueError, TypeError):
                    parsed = None
                if isinstance(parsed, list):
                    raw_val = parsed
                else:
                    raw_val = [v.strip() for v in raw_val.split(",") if v.strip()]
            else:
                return []
        # Remove duplicates preserving order
        seen = set()
        res = []
        for item in raw_val:
            s_item = str(item).strip()
            if s_item not in seen:
                seen.add(s_item)
                res.append(s_item)
        return res

    elif field_type in ("single_choice", "choice"):
        return str(raw_val).strip()

    elif field_type in ("integer", "decimal", "number"):
        val_str = str(raw_val).strip()
        try:
            if field_type == "integer":
                return int(val_str)
            if field_type == "number":
                normalized_num = (
                    val_str.replace(",", ".")
                    if "," in val_str and "." not in val_str
                    else val_str
                )
                if normalized_num.lstrip("+-").isdigit():
                    return int(normalized_num)
                return float(normalized_num)
            return float(val_str)
        except ValueError:
            return raw_val  # Pass through to fail validation

    elif field_type == "money":
        if isinstance(raw_val, dict):
            amt = raw_val.get("amount")
            if amt is not None:
                try:
                    amt_float = float(str(amt).strip())
                    raw_val["amount"] = (
                        int(amt_float) if amt_float.is_integer() else amt_float
                    )
                except ValueError:
                    pass
            cur = raw_val.get("currency")
            if cur is not None:
                raw_val["currency"] = str(cur).strip().upper()
            per = raw_val.get("period")
            if per is not None:
                raw_val["period"] = str(per).strip().lower()
            return raw_val
        return raw_val

    elif field_type == "phone":
        # Keep only digits, spaces, dashes and starting +
        val_str = str(raw_val).strip()
        cleaned = re.sub(r"[^\d\s\-\+]", "", val_str)
        return cleaned

    elif field_type == "person_name":
        if isinstance(raw_val, str):
            return {"fullName": raw_val.strip()}
        if isinstance(raw_val, dict) and "fullName" not in raw_val:
            parts = [
                str(v).strip()
                for v in raw_val.values()
                if v is not None and str(v).strip()
            ]
            if parts:
                return {"fullName": " ".join(parts)}
        return raw_val

    elif field_type == "date":
        val_str = str(raw_val).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(val_str, fmt).date().isoformat()
            except ValueError:
                continue
        return val_str

    elif field_type in ("string", "multiline_text", "email", "address"):
        if isinstance(raw_val, dict):
            parts = [
                str(v).strip()
                for v in raw_val.values()
                if v is not None and str(v).strip()
            ]
            return ", ".join(parts)
        return str(raw_val).strip()

    return raw_val
