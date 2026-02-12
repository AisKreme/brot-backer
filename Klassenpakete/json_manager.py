# Diese Datei ist für das Laden und Speichern von JSON-Daten zuständig.
# Sie kapselt alle Datei-Zugriffe, damit andere Klassen kein JSON-Wissen benötigen.

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Type, TypeVar

T = TypeVar("T")


class JsonManager:
    """
    Diese Klasse übernimmt das Laden und Speichern von Listen von Objekten
    (z. B. Mehl, BrotRezept) aus bzw. in JSON-Dateien.
    """

    def __init__(self, dateiPfad: str) -> None:
        self.standardSchemaVersion: int = 1

        # Immer den Datenordner unterhalb des Projektstamms verwenden
        projektPfad = Path(__file__).parent.parent
        datenOrdner = projektPfad / "daten"
        datenOrdner.mkdir(parents=True, exist_ok=True)
        self.dateiPfad: Path = datenOrdner / Path(dateiPfad).name

        # Falls die Datei noch nicht existiert, wird sie als Schema-Objekt angelegt
        if not self.dateiPfad.exists():
            self.dateiPfad.parent.mkdir(parents=True, exist_ok=True)
            self.dateiPfad.write_text(
                json.dumps(self._leeres_schema_objekt(), indent=4, ensure_ascii=False),
                encoding="utf-8",
            )

    def laden(self, klasse: Type[T]) -> List[T]:
        """
        Lädt eine JSON-Datei und erzeugt daraus eine Liste von Objekten
        der angegebenen Klasse.

        Wenn die Datei leer ist, wird eine leere Liste zurückgegeben.
        Die Klasse MUSS eine from_dict()-Methode besitzen.
        """
        if self.dateiPfad.stat().st_size == 0:
            return []

        roheDaten = self._lese_rohdaten()
        eintraege = self._extrahiere_eintraege(roheDaten)

        objekte: List[T] = [klasse.from_dict(eintrag) for eintrag in eintraege]

        return objekte

    def speichern(self, objekte: List[T]) -> None:
        """
        Speichert eine Liste von Objekten als JSON-Datei.

        Die Objekte MÜSSEN eine to_dict()-Methode besitzen.
        """
        datenZumSpeichern: list = []

        for objekt in objekte:
            datenZumSpeichern.append(objekt.to_dict())

        rohdaten = self._lese_rohdaten()
        if isinstance(rohdaten, dict):
            dokument = dict(rohdaten)
            schemaVersionRoh = dokument.get("schema_version", self.standardSchemaVersion)
            schemaVersion = (
                schemaVersionRoh
                if isinstance(schemaVersionRoh, int)
                else self.standardSchemaVersion
            )
        else:
            dokument = {}
            schemaVersion = self.standardSchemaVersion

        dokument["schema_version"] = schemaVersion
        dokument["updated_at"] = self._zeitstempel()
        dokument["items"] = datenZumSpeichern

        with self.dateiPfad.open("w", encoding="utf-8") as datei:
            json.dump(dokument, datei, indent=4, ensure_ascii=False)

    def _lese_rohdaten(self) -> dict[str, Any] | list[Any]:
        if self.dateiPfad.stat().st_size == 0:
            return self._leeres_schema_objekt()

        with self.dateiPfad.open("r", encoding="utf-8") as datei:
            try:
                return json.load(datei)
            except json.JSONDecodeError:
                return self._leeres_schema_objekt()

    def _extrahiere_eintraege(self, rohdaten: dict[str, Any] | list[Any]) -> list[Any]:
        # Abwärtskompatibel: alte Dateien mit reiner Listenstruktur weiter unterstützen
        if isinstance(rohdaten, list):
            return rohdaten

        if isinstance(rohdaten, dict):
            items = rohdaten.get("items", [])
            if isinstance(items, list):
                return items

        return []

    def _leeres_schema_objekt(self) -> dict[str, Any]:
        return {
            "schema_version": self.standardSchemaVersion,
            "updated_at": self._zeitstempel(),
            "items": [],
        }

    def _zeitstempel(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
