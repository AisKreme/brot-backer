from typing import Dict


class Mehl:
    """
    Repräsentiert ein einzelnes Mehl.
    Entspricht der JSON-Struktur in daten/mehle.json
    """

    def __init__(
        self,
        mehlArt: str,
        mehlTyp: str,
        eigenName: str,
        empfohleneHydration: str | int | None,
        vorhanden: bool = False,
        vorhandenGramm: int = 0,
        mehlId: str = "",
    ) -> None:
        # Stabile ID für Referenzen aus Rezepten/Backvorgängen
        self.id: str = mehlId

        # Art des Mehls, z.B. Weizen, Roggen, Dinkel
        self.mehlArt: str = mehlArt

        # Typ des Mehls, z.B. 405, 1050, Vollkorn
        self.mehlTyp: str = mehlTyp

        # Eigenname oder Herstellerbezeichnung
        self.eigenName: str = eigenName

        # Empfohlene Hydration als Text, z.B. "60-65%" oder "70"
        self.empfohleneHydration: str = (
            str(empfohleneHydration) if empfohleneHydration is not None else ""
        )

        # Gibt an, ob das Mehl aktuell vorhanden ist
        self.vorhanden: bool = vorhanden
        self.vorhandenGramm: int = vorhandenGramm

    def to_dict(self) -> Dict[str, object]:
        """
        Wandelt das Mehl-Objekt in ein Dictionary
        für die JSON-Speicherung um.
        """
        return {
            "id": self.id,
            "mehlArt": self.mehlArt,
            "mehlTyp": self.mehlTyp,
            "eigenName": self.eigenName,
            "empfohleneHydration": self.empfohleneHydration,
            "vorhanden": self.vorhanden,
            "vorhandenGramm": self.vorhandenGramm,
        }

    @classmethod
    def from_dict(cls, daten: Dict[str, object]) -> "Mehl":
        """
        Erzeugt ein Mehl-Objekt aus einem Dictionary.
        Falls 'vorhanden' fehlt (alte JSONs), wird True gesetzt.
        """
        return cls(
            mehlId=str(daten.get("id", "")),
            mehlArt=str(daten.get("mehlArt", "")),
            mehlTyp=str(daten.get("mehlTyp", "")),
            eigenName=str(daten.get("eigenName", "")),
            empfohleneHydration=str(daten.get("empfohleneHydration", "")),
            vorhanden=bool(daten.get("vorhanden", True)),
            vorhandenGramm=int(daten.get("vorhandenGramm", 0)),
        )

    def anzeigen(self) -> str:
        """
        Gibt eine gut lesbare Textdarstellung des Mehls zurück.
        """
        basisText: str = f"{self.mehlArt} Typ {self.mehlTyp}"

        if self.eigenName:
            basisText += f" ({self.eigenName}) "

        if self.empfohleneHydration:
            basisText += f"- ({self.empfohleneHydration})"

        return basisText
