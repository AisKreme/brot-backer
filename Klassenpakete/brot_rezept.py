from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Klassenpakete.zeiten import BackProfilPhase, ProzessSchritt
from Klassenpakete.zusatz import Zusatz


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
class MehlAnteil:
    mehl_id: str
    percent: float
    amount_g: float

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "MehlAnteil":
        return cls(
            mehl_id=str(daten.get("mehl_id", "")).strip(),
            percent=_to_float(daten.get("percent", 0)),
            amount_g=_to_float(daten.get("amount_g", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mehl_id": self.mehl_id,
            "percent": _normalize_number(self.percent),
            "amount_g": _normalize_number(self.amount_g),
        }


@dataclass
class Starter:
    amount_g: float
    hydration_percent: float

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "Starter":
        return cls(
            amount_g=_to_float(daten.get("amount_g", 0)),
            hydration_percent=_to_float(daten.get("hydration_percent", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount_g": _normalize_number(self.amount_g),
            "hydration_percent": _normalize_number(self.hydration_percent),
        }


@dataclass
class Formel:
    flours: list[MehlAnteil] = field(default_factory=list)
    water_g: float = 0.0
    salt_g: float = 0.0
    starter: Starter | None = None
    additional_ingredients: list[Zusatz] = field(default_factory=list)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "Formel":
        flours = [
            MehlAnteil.from_dict(eintrag)
            for eintrag in _as_list(daten.get("flours"))
            if isinstance(eintrag, dict)
        ]
        starter_roh = daten.get("starter")
        starter = Starter.from_dict(starter_roh) if isinstance(starter_roh, dict) else None
        additional_ingredients = [
            Zusatz.from_dict(eintrag)
            for eintrag in _as_list(daten.get("additional_ingredients"))
            if isinstance(eintrag, dict)
        ]

        return cls(
            flours=flours,
            water_g=_to_float(daten.get("water_g", 0)),
            salt_g=_to_float(daten.get("salt_g", 0)),
            starter=starter,
            additional_ingredients=additional_ingredients,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "flours": [eintrag.to_dict() for eintrag in self.flours],
            "water_g": _normalize_number(self.water_g),
            "salt_g": _normalize_number(self.salt_g),
            "starter": self.starter.to_dict() if self.starter else None,
            "additional_ingredients": [
                eintrag.to_dict() for eintrag in self.additional_ingredients
            ],
        }


@dataclass
class RezeptAusbeute:
    loaf_count_default: int = 1
    target_dough_weight_g: float = 0.0

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "RezeptAusbeute":
        return cls(
            loaf_count_default=_to_int(daten.get("loaf_count_default", 1), 1),
            target_dough_weight_g=_to_float(daten.get("target_dough_weight_g", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "loaf_count_default": self.loaf_count_default,
            "target_dough_weight_g": _normalize_number(self.target_dough_weight_g),
        }


@dataclass
class RezeptZiele:
    hydration_percent: float = 0.0
    dough_temp_c: float | None = None

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "RezeptZiele":
        return cls(
            hydration_percent=_to_float(daten.get("hydration_percent", 0)),
            dough_temp_c=_to_float_or_none(daten.get("dough_temp_c")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hydration_percent": _normalize_number(self.hydration_percent),
            "dough_temp_c": self.dough_temp_c,
        }


@dataclass
class BrotRezept:
    id: str
    name: str
    description: str = ""
    status: str = "active"
    version: int = 1
    tags: list[str] = field(default_factory=list)
    yield_data: RezeptAusbeute = field(default_factory=RezeptAusbeute)
    formula: Formel = field(default_factory=Formel)
    targets: RezeptZiele = field(default_factory=RezeptZiele)
    process_template: list[ProzessSchritt] = field(default_factory=list)
    bake_profile: list[BackProfilPhase] = field(default_factory=list)
    notes: str = ""
    custom: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    archived_at: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "BrotRezept":
        known_keys = {
            "id",
            "name",
            "description",
            "status",
            "version",
            "tags",
            "yield",
            "formula",
            "targets",
            "process_template",
            "bake_profile",
            "notes",
            "custom",
            "created_at",
            "updated_at",
            "archived_at",
        }
        extra_fields = {k: v for k, v in daten.items() if k not in known_keys}

        return cls(
            id=str(daten.get("id", "")).strip(),
            name=str(daten.get("name", "")).strip(),
            description=str(daten.get("description", "")).strip(),
            status=str(daten.get("status", "active")).strip() or "active",
            version=_to_int(daten.get("version", 1), 1),
            tags=[str(tag) for tag in _as_list(daten.get("tags"))],
            yield_data=RezeptAusbeute.from_dict(_as_dict(daten.get("yield"))),
            formula=Formel.from_dict(_as_dict(daten.get("formula"))),
            targets=RezeptZiele.from_dict(_as_dict(daten.get("targets"))),
            process_template=[
                ProzessSchritt.from_dict(eintrag)
                for eintrag in _as_list(daten.get("process_template"))
                if isinstance(eintrag, dict)
            ],
            bake_profile=[
                BackProfilPhase.from_dict(eintrag)
                for eintrag in _as_list(daten.get("bake_profile"))
                if isinstance(eintrag, dict)
            ],
            notes=str(daten.get("notes", "")).strip(),
            custom=_as_dict(daten.get("custom")),
            created_at=daten.get("created_at") if isinstance(daten.get("created_at"), str) else None,
            updated_at=daten.get("updated_at") if isinstance(daten.get("updated_at"), str) else None,
            archived_at=daten.get("archived_at") if isinstance(daten.get("archived_at"), str) else None,
            extra_fields=extra_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "version": self.version,
            "tags": self.tags,
            "yield": self.yield_data.to_dict(),
            "formula": self.formula.to_dict(),
            "targets": self.targets.to_dict(),
            "process_template": [eintrag.to_dict() for eintrag in self.process_template],
            "bake_profile": [eintrag.to_dict() for eintrag in self.bake_profile],
            "notes": self.notes,
        }

        if self.custom or "custom" in self.extra_fields:
            result["custom"] = self.custom
        if self.created_at is not None or "created_at" in self.extra_fields:
            result["created_at"] = self.created_at
        if self.updated_at is not None or "updated_at" in self.extra_fields:
            result["updated_at"] = self.updated_at
        if self.archived_at is not None or "archived_at" in self.extra_fields:
            result["archived_at"] = self.archived_at

        _merge_extra(result, self.extra_fields)
        return result
