from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return default

    return default


def _normalize_number(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return round(float(value), 3)


@dataclass
class Zusatz:
    """
    Zusatzzutat in Rezepten, z. B. Saaten, Oel oder Gewuerze.
    """

    name: str
    amount_g: float
    unit: str = "g"
    note: str = ""

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "Zusatz":
        return cls(
            name=str(daten.get("name", "")).strip(),
            amount_g=_to_float(daten.get("amount_g", 0)),
            unit=str(daten.get("unit", "g")).strip() or "g",
            note=str(daten.get("note", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        eintrag: dict[str, Any] = {
            "name": self.name,
            "amount_g": _normalize_number(self.amount_g),
        }

        # Nur speichern, wenn vom Standard abweichend.
        if self.unit and self.unit != "g":
            eintrag["unit"] = self.unit
        if self.note:
            eintrag["note"] = self.note

        return eintrag
