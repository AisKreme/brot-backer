# Dieses Modul enthält das Untermenü zur Verwaltung von Mehlen.
# Es nutzt das bestehende Menü-, Navigations- und JSON-System.

import re

from rich.prompt import Prompt

from Klassenpakete.json_manager import JsonManager
from Klassenpakete.mehl import Mehl
from Klassenpakete.menu import Menu


class MehleMenu:
    """
    Dieses Untermenü kapselt alle Aktionen rund um Mehle:
    Anzeigen, Hinzufügen (später auch Bearbeiten/Löschen).
    """

    MEHL_ARTEN: dict[str, list[str]] = {
        "Weizen": ["405", "550", "812", "1050", "1600", "00", "Vollkorn"],
        "Dinkel": ["630", "1050", "Vollkorn"],
        "Roggen": ["815", "1150", "Vollkorn"],
        "Urgetreide": ["Emmer", "Einkorn"],
    }

    def __init__(self) -> None:
        # Menüeinträge für die Mehlverwaltung
        self.menuePunkte: list[str] = [
            "Mehle anzeigen",
            "Neues Mehl hinzufügen",
            "Mehl bearbeiten",
            "Mehl löschen",
            "Zurück",
        ]

        self.menu: Menu = Menu(menuePunkte=self.menuePunkte)

        # JSON-Verwaltung für Mehle
        self.jsonManager: JsonManager = JsonManager("daten/mehle.json")

    def _slugify(self, text: str) -> str:
        """
        Erzeugt aus Freitext einen stabilen ASCII-Slug für IDs.
        """
        ersetzungen = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
            "Ä": "ae",
            "Ö": "oe",
            "Ü": "ue",
        }
        for alt, neu in ersetzungen.items():
            text = text.replace(alt, neu)

        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")

    def _generiere_mehl_id(
        self, mehlArt: str, mehlTyp: str, vorhandeneMehle: list[Mehl]
    ) -> str:
        basis = self._slugify(f"mehl_{mehlArt}_{mehlTyp}") or "mehl_unbekannt"
        vorhandeneIds: set[str] = {m.id for m in vorhandeneMehle if m.id}

        if basis not in vorhandeneIds:
            return basis

        suffix: int = 2
        while f"{basis}_{suffix}" in vorhandeneIds:
            suffix += 1
        return f"{basis}_{suffix}"

    def mehl_per_pfeiltasten_auswaehlen(
        self, mehle: list[Mehl], navigation
    ) -> Mehl | str | None:
        """
        Auswahl eines Mehls per Pfeiltasten.
        ENTER = Auswahl
        BACK  = Zurück
        SPACE = Bestand umschalten (0 ↔ Eingabe)
        """

        if not mehle:
            return None

        aktuellerIndex: int = 0

        while True:

            def render():
                return self.renderer.baue_mehle_tabelle(
                    mehle=mehle,
                    highlight_index=aktuellerIndex,
                    nur_vorhandene=False,
                )

            def input_handler(taste: str):
                nonlocal aktuellerIndex

                if taste == "UP":
                    aktuellerIndex = (aktuellerIndex - 1) % len(mehle)
                    return None

                elif taste == "DOWN":
                    aktuellerIndex = (aktuellerIndex + 1) % len(mehle)
                    return None

                elif taste == "ENTER":
                    return mehle[aktuellerIndex]

                elif taste == "BACK":
                    return "BACK"

                elif taste == "SPACE":
                    return "__SPACE__"

                return None

            result = self.renderer.render_loop(render, navigation, input_handler)

            # ENTER → echtes Mehl-Objekt zurückgeben
            if isinstance(result, Mehl):
                return result

            # BACK → Menü verlassen
            if result == "BACK":
                return "BACK"

            # SPACE → Bestand umschalten (außerhalb Live!)
            if result == "__SPACE__":
                mehl_aktuell: Mehl = mehle[aktuellerIndex]

                # Wenn Gramm > 0 → auf 0 setzen
                if mehl_aktuell.vorhandenGramm > 0:
                    mehl_aktuell.vorhandenGramm = 0
                    mehl_aktuell.vorhanden = False
                else:
                    # Eingabe NACH Beenden von Live
                    neueVorhandenGramm: str = self.prompt_gramm_eingabe(0)

                    if neueVorhandenGramm.isdigit() and int(neueVorhandenGramm) > 0:
                        mehl_aktuell.vorhandenGramm = int(neueVorhandenGramm)
                        mehl_aktuell.vorhanden = True
                    else:
                        mehl_aktuell.vorhandenGramm = 0
                        mehl_aktuell.vorhanden = False

                # Nach Änderung Loop neu starten → UI bleibt sauber
                continue

            # Sicherheitsabbruch
            return None

    def starten(self, navigation, renderer) -> None:
        """
        Startet die Ereignisschleife für das Mehle-Untermenü.
        """
        # zentrale LiveRenderer-Instanz für MehleMenu
        self.renderer = renderer
        while True:
            auswahlIndex = self.menu.anzeigen(navigation, renderer)

            if auswahlIndex == "BACK":
                return

            if not isinstance(auswahlIndex, int):
                return

            ausgewaehlterPunkt: str = self.menuePunkte[auswahlIndex]

            if ausgewaehlterPunkt == "Mehle anzeigen":
                self.mehle_anzeigen(navigation)
            elif ausgewaehlterPunkt == "Neues Mehl hinzufügen":
                self.neues_mehl_hinzufuegen(navigation)
            elif ausgewaehlterPunkt == "Mehl bearbeiten":
                self.mehl_bearbeiten(navigation)
            elif ausgewaehlterPunkt == "Mehl löschen":
                self.mehl_loeschen(navigation)
            elif ausgewaehlterPunkt == "Zurück":
                return

    def mehle_anzeigen(self, navigation) -> None:
        mehle: list[Mehl] = self.jsonManager.laden(Mehl)

        # Filter nur vorhandene Mehle
        mehle_vorhanden = [m for m in mehle if m.vorhanden]

        def render():
            return self.renderer.baue_mehle_tabelle(
                mehle=mehle_vorhanden, nur_vorhandene=True
            )

        def input_handler(taste: str):
            if taste in ("BACK", "ENTER", "ESC"):
                return taste
            return None

        self.renderer.render_loop(render, navigation, input_handler)

    def mehle_tabelle_anzeigen(
        self, mehle: list[Mehl], nur_vorhandene: bool, navigation
    ) -> None:
        aktuellerIndex: int = 0

        def render():
            return self.renderer.baue_mehle_tabelle(
                mehle=mehle,
                highlight_index=aktuellerIndex,
                nur_vorhandene=nur_vorhandene,
            )

        def input_handler(taste: str):
            nonlocal aktuellerIndex

            if taste in ("BACK", "ENTER", "ESC"):
                return taste
            # Pfeiltasten zur Bewegung des Highlight
            elif taste == "UP":
                aktuellerIndex = (aktuellerIndex - 1) % len(mehle)
                return None
            elif taste == "DOWN":
                aktuellerIndex = (aktuellerIndex + 1) % len(mehle)
                return None
            else:
                return None

        self.renderer.render_loop(render, navigation, input_handler)

    def neues_mehl_hinzufuegen(self, navigation) -> None:
        """
        Erfragt alle notwendigen Daten für ein neues Mehl
        und speichert es dauerhaft in der JSON-Datei.
        """
        with self.renderer.suspended():
            print("\nNeues Mehl hinzufügen\n")

        # Mehlart auswählen über Pfeiltasten
        mehlArten: list[str] = list(self.MEHL_ARTEN.keys())

        menuArt = Menu(mehlArten)
        auswahlArt = menuArt.anzeigen(navigation, self.renderer)
        if auswahlArt is None:
            return
        mehlArt = mehlArten[auswahlArt]

        mehlTypen: list[str] = self.MEHL_ARTEN[mehlArt]
        menuTyp = Menu(mehlTypen)
        auswahlTyp = menuTyp.anzeigen(navigation, self.renderer)
        if auswahlTyp is None:
            return
        mehlTyp = mehlTypen[auswahlTyp]

        # Eingabe
        with self.renderer.suspended():
            eigenName: str = input("Eigenname / Hersteller (optional): ").strip()
            hydrationEingabe: str = input(
                "Empfohlene Hydration in % (optional, z.B. 70): "
            ).strip()

        empfohleneHydration: int | None = None
        if hydrationEingabe:
            if hydrationEingabe.isdigit():
                empfohleneHydration = int(hydrationEingabe)
            else:
                with self.renderer.suspended():
                    print("Warnung: Ungültige Hydration, Wert wird ignoriert.")

        # Bestehende Mehle laden
        mehle: list[Mehl] = self.jsonManager.laden(Mehl)

        # Neues Mehl-Objekt erstellen
        neuesMehl: Mehl = Mehl(
            mehlArt=mehlArt,
            mehlTyp=mehlTyp,
            eigenName=eigenName,
            empfohleneHydration=empfohleneHydration,
            vorhanden=True,
            mehlId=self._generiere_mehl_id(mehlArt, mehlTyp, mehle),
        )

        # Dubletten prüfen (Mehlart + Mehltyp)
        for vorhandenesMehl in mehle:
            if (
                vorhandenesMehl.mehlArt == neuesMehl.mehlArt
                and vorhandenesMehl.mehlTyp == neuesMehl.mehlTyp
            ):
                with self.renderer.suspended():
                    print("\n❌ Dieses Mehl existiert bereits!")
                    print(vorhandenesMehl.anzeigen())
                    input("\nENTER drücken, um zurückzukehren...")
                return

        # Neues Mehl hinzufügen
        mehle.append(neuesMehl)

        # Alles speichern
        self.jsonManager.speichern(mehle)

        with self.renderer.suspended():
            print("\nMehl wurde erfolgreich gespeichert:")
            print(neuesMehl.anzeigen())
            input("\nENTER drücken, um zurückzukehren...")

    def prompt_gramm_eingabe(self, startwert: int) -> str:
        """
        Zeigt ein Eingabefeld für die vorhandene Grammzahl an.
        startwert: der aktuelle Wert, der als Standard angezeigt wird.
        Gibt die eingegebene Zahl als String zurück.
        """
        with self.renderer.suspended():
            eingabe: str = Prompt.ask(f"Vorhandene Gramm [{startwert}]")
        return eingabe.strip()

    def mehl_bearbeiten(self, navigation) -> None:
        """
        Ermöglicht das Bearbeiten eines bestehenden Mehls.
        """
        mehle: list[Mehl] = self.jsonManager.laden(Mehl)

        if not mehle:
            with self.renderer.suspended():
                print("\nKeine Mehle zum Bearbeiten vorhanden.")
                input("ENTER drücken, um zurückzukehren...")
            return

        mehl = self.mehl_per_pfeiltasten_auswaehlen(mehle, navigation)

        # Wenn kein echtes Mehl-Objekt zurückgegeben wurde → abbrechen
        if isinstance(mehl, Mehl):
            with self.renderer.suspended():
                print("\nFelder leer lassen, um den aktuellen Wert zu behalten.\n")
                neueArt: str = input(f"Mehlart [{mehl.mehlArt}]: ").strip()
                neuerTyp: str = input(f"Mehltyp [{mehl.mehlTyp}]: ").strip()
                neuerEigenName: str = input(f"Eigenname [{mehl.eigenName}]: ").strip()
                neueHydration: str = input(
                    f"Hydration [{mehl.empfohleneHydration}]: "
                ).strip()

            if neueArt:
                mehl.mehlArt = neueArt

            if neuerTyp:
                mehl.mehlTyp = neuerTyp

            if neuerEigenName:
                mehl.eigenName = neuerEigenName

            if neueHydration:
                if neueHydration.isdigit():
                    mehl.empfohleneHydration = int(neueHydration)
                else:
                    with self.renderer.suspended():
                        print("Ungültige Hydration, alter Wert bleibt erhalten.")

            statusText: str = "ja" if mehl.vorhanden else "nein"
            with self.renderer.suspended():
                statusEingabe: str = (
                    input(f"Mehl vorhanden? (j/n) [{statusText}]: ").strip().lower()
                )

            if statusEingabe == "j":
                mehl.vorhanden = True
                with self.renderer.suspended():
                    neueVorhandenGramm: str = input(
                        f"Vorhandene Gramm [{mehl.vorhandenGramm}]: "
                    ).strip()
                if neueVorhandenGramm:
                    if neueVorhandenGramm.isdigit():
                        mehl.vorhandenGramm = int(neueVorhandenGramm)
                    else:
                        with self.renderer.suspended():
                            print("Ungültige Grammanzahl, alter Wert bleibt erhalten.")
            elif statusEingabe == "n":
                mehl.vorhanden = False
                mehl.vorhandenGramm = 0

            self.jsonManager.speichern(mehle)

            with self.renderer.suspended():
                print("\nMehl wurde aktualisiert:")
                print(mehl.anzeigen())
                input("\nENTER drücken, um zurückzukehren...")
        else:
            return

    def mehl_loeschen(self, navigation) -> None:
        """
        Löscht ein bestehendes Mehl nach Bestätigung.
        """
        mehle: list[Mehl] = self.jsonManager.laden(Mehl)

        if not mehle:
            with self.renderer.suspended():
                print("\nKeine Mehle zum Löschen vorhanden.")
                input("ENTER drücken, um zurückzukehren...")
            return

        mehl = self.mehl_per_pfeiltasten_auswaehlen(mehle, navigation)

        # Wenn kein echtes Mehl-Objekt zurückgegeben wurde → abbrechen
        if not isinstance(mehl, Mehl):
            return

        if mehl.vorhanden:
            with self.renderer.suspended():
                print("\n❌ Dieses Mehl ist noch als VORHANDEN markiert.")
                print("Es kann erst gelöscht werden, wenn es NICHT VORHANDEN ist.")
                input("ENTER drücken, um zurückzukehren...")
            return

        with self.renderer.suspended():
            bestaetigung: str = (
                input(f'\nMehl "{mehl.anzeigen()}" wirklich löschen? (j/n): ')
                .strip()
                .lower()
            )

        if bestaetigung != "j":
            with self.renderer.suspended():
                print("Löschen abgebrochen.")
                input("ENTER drücken, um zurückzukehren...")
            return

        mehle.remove(mehl)
        self.jsonManager.speichern(mehle)

        with self.renderer.suspended():
            print("\nMehl wurde gelöscht.")
            input("ENTER drücken, um zurückzukehren...")
