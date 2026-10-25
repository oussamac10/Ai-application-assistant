# Normalized Form Schema

Every predefined template and every dynamically analyzed PDF bridges into an immutable `FormVersion` containing ordered `FormField` records (`backend/app/forms/models.py`).

## Field Schema Attributes

- `key`: Stable identifier within the `FormVersion` (e.g., `first_name`, `move_in_date`, `signature_tenant`).
- `field_type`: Canonical input type (`string`, `multiline_text`, `date`, `integer`, `decimal`, `money`, `boolean`, `single_choice`, `multiple_choice`, `email`, `phone`, `address`, `country`, `person_name`, `signature`).
- `required_state`: Three-state requiredness (`required`, `optional`, `unknown`) — see [ADR 0016](decisions/0016-three-state-requiredness-and-structured-confirmation.md).
- `labels` & `help_texts`: Language-keyed maps (`{"de": "Einzugsdatum", "en": "Move-in date", "ar": "تاريخ الانتقال"}`).
- `configuration`: Semantic `question_key`, `page_number`, normalized `bounding_box` (`{x, y, width, height}` in `[0..1]` page ratios), AcroForm widget target, and validation constraints.

## Canonical References

- [Form Model Specification](form-model.md)
- [Field Detection & Bridging](field-detection.md)
- [AI & Document Processing Pipeline (`AI_PIPELINE.md`)](AI_PIPELINE.md)
