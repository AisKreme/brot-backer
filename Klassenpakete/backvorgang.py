from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_number(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return round(float(value), 3)


def _merge_extra(result: dict[str, Any], extra_fields: dict[str, Any]) -> None:
    for key, value in extra_fields.items():
        if key not in result:
            result[key] = value


@dataclass
class RezeptSnapshot:
    name: str = ""
    hydration_percent: float | None = None

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "RezeptSnapshot":
        return cls(
            name=str(daten.get("name", "")).strip(),
            hydration_percent=_to_float_or_none(daten.get("hydration_percent")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "hydration_percent": self.hydration_percent,
        }


@dataclass
class BackZiel:
    loaf_count: int = 1
    target_dough_weight_g: float = 0.0

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "BackZiel":
        return cls(
            loaf_count=_to_int(daten.get("loaf_count", 1), 1),
            target_dough_weight_g=_to_float(daten.get("target_dough_weight_g", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "loaf_count": self.loaf_count,
            "target_dough_weight_g": _normalize_number(self.target_dough_weight_g),
        }


@dataclass
class ZutatenVerbrauch:
    mehl_id: str
    planned_g: float = 0.0
    actual_g: float = 0.0
    stock_deducted_g: float = 0.0
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "ZutatenVerbrauch":
        known_keys = {"mehl_id", "planned_g", "actual_g", "stock_deducted_g"}
        extra_fields = {k: v for k, v in daten.items() if k not in known_keys}

        mehl_id_roh = daten.get("mehl_id", daten.get("ingredient_id", ""))
        return cls(
            mehl_id=str(mehl_id_roh).strip(),
            planned_g=_to_float(daten.get("planned_g", 0)),
            actual_g=_to_float(daten.get("actual_g", 0)),
            stock_deducted_g=_to_float(daten.get("stock_deducted_g", 0)),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mehl_id": self.mehl_id,
            "planned_g": _normalize_number(self.planned_g),
            "actual_g": _normalize_number(self.actual_g),
            "stock_deducted_g": _normalize_number(self.stock_deducted_g),
        }
        _merge_extra(result, self.extra_fields)
        return result


@dataclass
class SchrittDurchlauf:
    key: str
    planned_duration_min: int
    actual_start_at: str | None = None
    actual_end_at: str | None = None
    actual_duration_min: int | None = None
    avg_temp_c: float | None = None
    note: str = ""
    label: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "SchrittDurchlauf":
        known_keys = {
            "key",
            "label",
            "planned_duration_min",
            "actual_start_at",
            "actual_end_at",
            "actual_duration_min",
            "avg_temp_c",
            "note",
        }
        extra_fields = {k: v for k, v in daten.items() if k not in known_keys}

        return cls(
            key=str(daten.get("key", "")).strip(),
            label=str(daten.get("label")).strip() if "label" in daten else None,
            planned_duration_min=_to_int(daten.get("planned_duration_min", 0)),
            actual_start_at=(
                str(daten.get("actual_start_at"))
                if isinstance(daten.get("actual_start_at"), str)
                else None
            ),
            actual_end_at=(
                str(daten.get("actual_end_at"))
                if isinstance(daten.get("actual_end_at"), str)
                else None
            ),
            actual_duration_min=(
                _to_int(daten.get("actual_duration_min"))
                if daten.get("actual_duration_min") is not None
                else None
            ),
            avg_temp_c=_to_float_or_none(daten.get("avg_temp_c")),
            note=str(daten.get("note", "")).strip(),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "key": self.key,
            "planned_duration_min": self.planned_duration_min,
            "actual_start_at": self.actual_start_at,
            "actual_end_at": self.actual_end_at,
            "actual_duration_min": self.actual_duration_min,
            "avg_temp_c": self.avg_temp_c,
            "note": self.note,
        }
        if self.label is not None or "label" in self.extra_fields:
            result["label"] = self.label

        _merge_extra(result, self.extra_fields)
        return result


@dataclass
class BackErgebnis:
    rating: int | None = None
    crumb: str = ""
    crust: str = ""
    volume: str = ""
    taste_note: str = ""
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "BackErgebnis":
        known_keys = {"rating", "crumb", "crust", "volume", "taste_note"}
        extra_fields = {k: v for k, v in daten.items() if k not in known_keys}

        rating = _to_int(daten.get("rating")) if daten.get("rating") is not None else None
        return cls(
            rating=rating,
            crumb=str(daten.get("crumb", "")).strip(),
            crust=str(daten.get("crust", "")).strip(),
            volume=str(daten.get("volume", "")).strip(),
            taste_note=str(daten.get("taste_note", "")).strip(),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "rating": self.rating,
            "crumb": self.crumb,
            "crust": self.crust,
            "volume": self.volume,
            "taste_note": self.taste_note,
        }
        _merge_extra(result, self.extra_fields)
        return result


@dataclass
class Backvorgang:
    id: str
    recipe_id: str
    recipe_version: int = 1
    recipe_snapshot: RezeptSnapshot = field(default_factory=RezeptSnapshot)
    status: str = "planned"
    planned_bake_date: str = ""
    started_at: str | None = None
    ended_at: str | None = None
    scale_factor: float = 1.0
    target: BackZiel = field(default_factory=BackZiel)
    ingredient_usage: list[ZutatenVerbrauch] = field(default_factory=list)
    step_runs: list[SchrittDurchlauf] = field(default_factory=list)
    measurements: list[dict[str, Any]] = field(default_factory=list)
    outcome: BackErgebnis = field(default_factory=BackErgebnis)
    issues: list[str] = field(default_factory=list)
    notes: str = ""
    attachments: list[Any] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "Backvorgang":
        known_keys = {
            "id",
            "recipe_id",
            "recipe_version",
            "recipe_snapshot",
            "status",
            "planned_bake_date",
            "started_at",
            "ended_at",
            "scale_factor",
            "target",
            "ingredient_usage",
            "step_runs",
            "measurements",
            "outcome",
            "issues",
            "notes",
            "attachments",
            "custom",
            "created_at",
            "updated_at",
        }
        extra_fields = {k: v for k, v in daten.items() if k not in known_keys}

        return cls(
            id=str(daten.get("id", "")).strip(),
            recipe_id=str(daten.get("recipe_id", "")).strip(),
            recipe_version=_to_int(daten.get("recipe_version", 1), 1),
            recipe_snapshot=RezeptSnapshot.from_dict(_as_dict(daten.get("recipe_snapshot"))),
            status=str(daten.get("status", "planned")).strip() or "planned",
            planned_bake_date=str(daten.get("planned_bake_date", "")).strip(),
            started_at=str(daten.get("started_at")) if isinstance(daten.get("started_at"), str) else None,
            ended_at=str(daten.get("ended_at")) if isinstance(daten.get("ended_at"), str) else None,
            scale_factor=_to_float(daten.get("scale_factor", 1.0), 1.0),
            target=BackZiel.from_dict(_as_dict(daten.get("target"))),
            ingredient_usage=[
                ZutatenVerbrauch.from_dict(eintrag)
                for eintrag in _as_list(daten.get("ingredient_usage"))
                if isinstance(eintrag, dict)
            ],
            step_runs=[
                SchrittDurchlauf.from_dict(eintrag)
                for eintrag in _as_list(daten.get("step_runs"))
                if isinstance(eintrag, dict)
            ],
            measurements=[
                eintrag
                for eintrag in _as_list(daten.get("measurements"))
                if isinstance(eintrag, dict)
            ],
            outcome=BackErgebnis.from_dict(_as_dict(daten.get("outcome"))),
            issues=[str(issue) for issue in _as_list(daten.get("issues"))],
            notes=str(daten.get("notes", "")).strip(),
            attachments=list(_as_list(daten.get("attachments"))),
            custom=_as_dict(daten.get("custom")),
            created_at=str(daten.get("created_at")) if isinstance(daten.get("created_at"), str) else None,
            updated_at=str(daten.get("updated_at")) if isinstance(daten.get("updated_at"), str) else None,
            extra_fields=extra_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "recipe_id": self.recipe_id,
            "recipe_version": self.recipe_version,
            "recipe_snapshot": self.recipe_snapshot.to_dict(),
            "status": self.status,
            "planned_bake_date": self.planned_bake_date,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "scale_factor": _normalize_number(self.scale_factor),
            "target": self.target.to_dict(),
            "ingredient_usage": [eintrag.to_dict() for eintrag in self.ingredient_usage],
            "step_runs": [eintrag.to_dict() for eintrag in self.step_runs],
            "measurements": self.measurements,
            "outcome": self.outcome.to_dict(),
            "issues": self.issues,
            "notes": self.notes,
            "attachments": self.attachments,
            "custom": self.custom,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        _merge_extra(result, self.extra_fields)
        return result
