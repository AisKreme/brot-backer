from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class ProzessSchritt:
    """
    Geplanter Prozessschritt im Rezept-Template.
    """

    key: str
    label: str
    duration_min: int
    target_temp_c: float | None = None

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "ProzessSchritt":
        return cls(
            key=str(daten.get("key", "")).strip(),
            label=str(daten.get("label", "")).strip(),
            duration_min=_to_int(daten.get("duration_min", 0)),
            target_temp_c=_to_float_or_none(daten.get("target_temp_c")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "duration_min": self.duration_min,
            "target_temp_c": self.target_temp_c,
        }


@dataclass
class BackProfilPhase:
    """
    Einzelne Backphase mit Temperatur und Dampf.
    """

    phase: str
    duration_min: int
    temp_c: float
    steam: bool

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "BackProfilPhase":
        return cls(
            phase=str(daten.get("phase", "")).strip(),
            duration_min=_to_int(daten.get("duration_min", 0)),
            temp_c=float(daten.get("temp_c", 0)),
            steam=bool(daten.get("steam", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "duration_min": self.duration_min,
            "temp_c": self.temp_c,
            "steam": self.steam,
        }
