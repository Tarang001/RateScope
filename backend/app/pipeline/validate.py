from pydantic import ValidationError

from app.schemas.events import SupplierEvent


def parse_event(payload: dict) -> tuple[SupplierEvent | None, str | None]:
    if not isinstance(payload, dict):
        return None, "payload_not_object"
    try:
        event = SupplierEvent.model_validate(payload)
        return event, None
    except ValidationError as exc:
        return None, f"validation_error:{exc.error_count()}"
