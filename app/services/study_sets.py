from typing import Any, Dict

from fastapi import HTTPException

from app.core.study_set_generator import ALLOWED_STUDY_SET_TYPES


def normalize_study_set_type(study_type: str) -> str:
    normalized = (study_type or "").strip().lower()
    if normalized not in ALLOWED_STUDY_SET_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported study set type")
    return normalized


def build_study_set_record(
    generated: Dict[str, Any],
    *,
    study_type: str,
    source_filename: str,
    difficulty: str,
    model: str,
) -> Dict[str, Any]:
    items = generated.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError("Generated study set did not include items")

    return {
        "type": study_type,
        "title": generated.get("title") or "Study Set",
        "source_filename": source_filename,
        "items": items,
        "model": model,
        "difficulty": difficulty,
        "item_count": len(items),
    }
