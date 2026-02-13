from __future__ import annotations

from datetime import datetime

from Klassenpakete.brot_rezept import BrotRezept
from Klassenpakete.json_manager import JsonManager
from Klassenpakete.menu import Menu
from Klassenpakete.zeiten import BackProfilPhase, ProzessSchritt
from Klassenpakete.ui_layout import MAX_ZEILEN_STANDARD, baue_standard_tabelle, kuerze_text


class RezepteMenu:
    """
    Untermenue fuer Rezeptansicht und Rezeptbearbeitung.
    """

    def __init__(self) -> None:
        self.menuePunkte: list[str] = [
            "Rezepte anzeigen",
            "Rezept bearbeiten",
            "Zurueck",
        ]
        self.menu: Menu = Menu(menuePunkte=self.menuePunkte)
        self.rezeptManager: JsonManager = JsonManager("daten/brote.json")

    def starten(self, navigation, renderer) -> None:
        self.renderer = renderer

        while True:
            auswahlIndex = self.menu.anzeigen(navigation, renderer)

            if auswahlIndex == "BACK":
                return

            if not isinstance(auswahlIndex, int):
                return

            ausgewaehlterPunkt = self.menuePunkte[auswahlIndex]
            if ausgewaehlterPunkt == "Rezepte anzeigen":
                self.rezepte_anzeigen(navigation)
            elif ausgewaehlterPunkt == "Rezept bearbeiten":
                self.rezept_bearbeiten(navigation)
            elif ausgewaehlterPunkt == "Zurueck":
                return

    def rezepte_anzeigen(self, navigation) -> None:
        rezepte = self.rezeptManager.laden(BrotRezept)

        def render():
            tabelle = baue_standard_tabelle(
                titel="Brot-Backer | Rezepte",
                caption="ENTER oder BACK fuer Zurueck",
            )
            tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
            tabelle.add_column(
                "Name",
                style="bold white",
                overflow="ellipsis",
                no_wrap=True,
                max_width=20,
            )
            tabelle.add_column(
                "ID",
                style="magenta",
                overflow="ellipsis",
                no_wrap=True,
                max_width=18,
            )
            tabelle.add_column("Status", style="cyan", width=9)
            tabelle.add_column("Hydr. %", style="green", justify="right", width=8)
            tabelle.add_column("Wasser g", style="yellow", justify="right", width=9)

            if not rezepte:
                tabelle.add_row("-", "Keine Rezepte vorhanden", "-", "-", "-", "-")
                return tabelle

            sichtbare = rezepte[:MAX_ZEILEN_STANDARD]
            for index, rezept in enumerate(sichtbare, start=1):
                hydration = f"{rezept.targets.hydration_percent:.1f}"
                wasser = f"{rezept.formula.water_g:.1f}"
                tabelle.add_row(
                    str(index),
                    kuerze_text(rezept.name, 20),
                    kuerze_text(rezept.id, 18),
                    kuerze_text(rezept.status, 9),
                    hydration,
                    wasser,
                )

            if len(rezepte) > MAX_ZEILEN_STANDARD:
                rest = len(rezepte) - MAX_ZEILEN_STANDARD
                tabelle.add_row("...", f"... {rest} weitere", "-", "-", "-", "-")

            return tabelle

        def input_handler(taste: str):
            if taste in ("BACK", "ENTER", "ESC"):
                return taste
            return None

        self.renderer.render_loop(render, navigation, input_handler)

    def rezept_bearbeiten(self, navigation) -> None:
        rezepte = self.rezeptManager.laden(BrotRezept)
        if not rezepte:
            with self.renderer.suspended():
                print("\nKeine Rezepte zum Bearbeiten vorhanden.")
                input("ENTER druecken, um zurueckzukehren...")
            return

        eintraege = [
            f"{rezept.name} | {rezept.id} | v{rezept.version} | {rezept.status}"
            for rezept in rezepte
        ]
        auswahl = Menu(eintraege).anzeigen(navigation, self.renderer)
        if not isinstance(auswahl, int):
            return

        rezept = rezepte[auswahl]
        with self.renderer.suspended():
            print("\nRezept bearbeiten (leer = alten Wert behalten)\n")
            name = input(f"Name [{rezept.name}]: ").strip()
            beschreibung = input(f"Beschreibung [{rezept.description}]: ").strip()
            status = input(f"Status [{rezept.status}] (active/archived): ").strip()
            tags_roh = input(
                f"Tags komma-getrennt [{', '.join(rezept.tags)}]: "
            ).strip()
            hydration_roh = input(
                f"Hydration % [{rezept.targets.hydration_percent}]: "
            ).strip()
            wasser_roh = input(f"Wasser g [{rezept.formula.water_g}]: ").strip()
            salz_roh = input(f"Salz g [{rezept.formula.salt_g}]: ").strip()
            ziel_roh = input(
                f"Zielteiggewicht g [{rezept.yield_data.target_dough_weight_g}]: "
            ).strip()
            loaves_roh = input(
                f"Standard-Laibzahl [{rezept.yield_data.loaf_count_default}]: "
            ).strip()
            notes = input(
                f"Notizen [{kuerze_text(rezept.notes, 60)}] ('-' fuer leeren Wert): "
            ).strip()

        if name:
            rezept.name = name
        if beschreibung:
            rezept.description = beschreibung
        if status:
            if status in ("active", "archived"):
                rezept.status = status
            else:
                with self.renderer.suspended():
                    print("Ungueltiger Status, alter Wert bleibt erhalten.")
        if tags_roh:
            rezept.tags = [tag.strip() for tag in tags_roh.split(",") if tag.strip()]

        hydration = self._parse_float_oder_none(hydration_roh)
        if hydration is not None:
            rezept.targets.hydration_percent = hydration

        wasser = self._parse_float_oder_none(wasser_roh)
        if wasser is not None:
            rezept.formula.water_g = wasser

        salz = self._parse_float_oder_none(salz_roh)
        if salz is not None:
            rezept.formula.salt_g = salz

        ziel = self._parse_float_oder_none(ziel_roh)
        if ziel is not None:
            rezept.yield_data.target_dough_weight_g = ziel

        loaves = self._parse_int_oder_none(loaves_roh)
        if loaves is not None and loaves > 0:
            rezept.yield_data.loaf_count_default = loaves

        if notes == "-":
            rezept.notes = ""
        elif notes:
            rezept.notes = notes

        with self.renderer.suspended():
            prozess_bearbeiten = (
                input("Prozessschritte bearbeiten? (j/n) [n]: ").strip().lower()
            )
        if prozess_bearbeiten in ("j", "ja", "y", "yes"):
            self._bearbeite_prozessschritte(rezept)

        with self.renderer.suspended():
            backprofil_bearbeiten = (
                input("Backprofil bearbeiten? (j/n) [n]: ").strip().lower()
            )
        if backprofil_bearbeiten in ("j", "ja", "y", "yes"):
            self._bearbeite_backprofil(rezept)

        rezept.version = max(1, rezept.version) + 1
        rezept.updated_at = datetime.now().astimezone().isoformat(timespec="seconds")

        self.rezeptManager.speichern(rezepte)

        with self.renderer.suspended():
            print("\nRezept aktualisiert.")
            print(f"ID: {rezept.id}")
            print(f"Neue Version: {rezept.version}")
            input("ENTER druecken, um zurueckzukehren...")

    def _parse_float_oder_none(self, rohwert: str) -> float | None:
        text = rohwert.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _parse_int_oder_none(self, rohwert: str) -> int | None:
        text = rohwert.strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        return None

    def _bearbeite_prozessschritte(self, rezept: BrotRezept) -> None:
        while True:
            with self.renderer.suspended():
                self.renderer.console.print(
                    self._baue_prozessschritte_tabelle(rezept.process_template)
                )
                print(
                    "\nAktion: [a] Schritt hinzufuegen | [b] Schritt bearbeiten | "
                    "[d] Schritt loeschen | [q] fertig"
                )
                aktion = input("Auswahl: ").strip().lower()

            if aktion in ("q", ""):
                return

            if aktion == "a":
                self._prozessschritt_hinzufuegen(rezept)
            elif aktion == "b":
                self._prozessschritt_bearbeiten(rezept)
            elif aktion == "d":
                self._prozessschritt_loeschen(rezept)

    def _prozessschritt_hinzufuegen(self, rezept: BrotRezept) -> None:
        with self.renderer.suspended():
            print("\nNeuer Prozessschritt")
            key = input("Key (z.B. stockgare): ").strip().lower().replace(" ", "_")
            label = input("Label (anzeigename): ").strip()
            dauer_roh = input("Dauer in Minuten: ").strip()
            temp_roh = input("Zieltemperatur C (optional): ").strip()

        dauer = self._parse_int_oder_none(dauer_roh)
        if dauer is None or dauer <= 0:
            dauer = 1

        target_temp = self._parse_float_oder_none(temp_roh)
        if not key:
            key = f"schritt_{len(rezept.process_template) + 1}"
        if not label:
            label = key

        rezept.process_template.append(
            ProzessSchritt(
                key=key,
                label=label,
                duration_min=dauer,
                target_temp_c=target_temp,
            )
        )

    def _prozessschritt_bearbeiten(self, rezept: BrotRezept) -> None:
        if not rezept.process_template:
            return

        with self.renderer.suspended():
            index_roh = input("Schritt-Nr. zum Bearbeiten: ").strip()
        index = self._parse_int_oder_none(index_roh)
        if index is None or not (1 <= index <= len(rezept.process_template)):
            return

        schritt = rezept.process_template[index - 1]
        with self.renderer.suspended():
            key = input(f"Key [{schritt.key}]: ").strip().lower().replace(" ", "_")
            label = input(f"Label [{schritt.label}]: ").strip()
            dauer_roh = input(f"Dauer Min [{schritt.duration_min}]: ").strip()
            temp_roh = input(
                f"Zieltemp C [{schritt.target_temp_c}] ('-' fuer leer): "
            ).strip()

        if key:
            schritt.key = key
        if label:
            schritt.label = label
        dauer = self._parse_int_oder_none(dauer_roh)
        if dauer is not None and dauer > 0:
            schritt.duration_min = dauer
        if temp_roh == "-":
            schritt.target_temp_c = None
        else:
            temp = self._parse_float_oder_none(temp_roh)
            if temp is not None:
                schritt.target_temp_c = temp

    def _prozessschritt_loeschen(self, rezept: BrotRezept) -> None:
        if not rezept.process_template:
            return

        with self.renderer.suspended():
            index_roh = input("Schritt-Nr. zum Loeschen: ").strip()
        index = self._parse_int_oder_none(index_roh)
        if index is None or not (1 <= index <= len(rezept.process_template)):
            return
        del rezept.process_template[index - 1]

    def _bearbeite_backprofil(self, rezept: BrotRezept) -> None:
        while True:
            with self.renderer.suspended():
                self.renderer.console.print(
                    self._baue_backprofil_tabelle(rezept.bake_profile)
                )
                print(
                    "\nAktion: [a] Phase hinzufuegen | [b] Phase bearbeiten | "
                    "[d] Phase loeschen | [q] fertig"
                )
                aktion = input("Auswahl: ").strip().lower()

            if aktion in ("q", ""):
                return

            if aktion == "a":
                self._backprofil_hinzufuegen(rezept)
            elif aktion == "b":
                self._backprofil_bearbeiten(rezept)
            elif aktion == "d":
                self._backprofil_loeschen(rezept)

    def _backprofil_hinzufuegen(self, rezept: BrotRezept) -> None:
        with self.renderer.suspended():
            print("\nNeue Backprofil-Phase")
            phase = input("Phase (z.B. anbacken): ").strip()
            dauer_roh = input("Dauer in Minuten: ").strip()
            temp_roh = input("Temperatur in C: ").strip()
            steam_roh = input("Dampf? (j/n) [n]: ").strip().lower()

        dauer = self._parse_int_oder_none(dauer_roh)
        if dauer is None or dauer <= 0:
            dauer = 1

        temp = self._parse_float_oder_none(temp_roh)
        if temp is None:
            temp = 0.0

        if not phase:
            phase = f"phase_{len(rezept.bake_profile) + 1}"

        rezept.bake_profile.append(
            BackProfilPhase(
                phase=phase,
                duration_min=dauer,
                temp_c=temp,
                steam=steam_roh in ("j", "ja", "y", "yes"),
            )
        )

    def _backprofil_bearbeiten(self, rezept: BrotRezept) -> None:
        if not rezept.bake_profile:
            return

        with self.renderer.suspended():
            index_roh = input("Phase-Nr. zum Bearbeiten: ").strip()
        index = self._parse_int_oder_none(index_roh)
        if index is None or not (1 <= index <= len(rezept.bake_profile)):
            return

        phase = rezept.bake_profile[index - 1]
        with self.renderer.suspended():
            phase_name = input(f"Phase [{phase.phase}]: ").strip()
            dauer_roh = input(f"Dauer Min [{phase.duration_min}]: ").strip()
            temp_roh = input(f"Temperatur C [{phase.temp_c}]: ").strip()
            steam_roh = input(
                f"Dampf? (j/n) [{'j' if phase.steam else 'n'}]: "
            ).strip().lower()

        if phase_name:
            phase.phase = phase_name

        dauer = self._parse_int_oder_none(dauer_roh)
        if dauer is not None and dauer > 0:
            phase.duration_min = dauer

        temp = self._parse_float_oder_none(temp_roh)
        if temp is not None:
            phase.temp_c = temp

        if steam_roh in ("j", "ja", "y", "yes"):
            phase.steam = True
        elif steam_roh in ("n", "no", "nein"):
            phase.steam = False

    def _backprofil_loeschen(self, rezept: BrotRezept) -> None:
        if not rezept.bake_profile:
            return

        with self.renderer.suspended():
            index_roh = input("Phase-Nr. zum Loeschen: ").strip()
        index = self._parse_int_oder_none(index_roh)
        if index is None or not (1 <= index <= len(rezept.bake_profile)):
            return
        del rezept.bake_profile[index - 1]

    def _baue_prozessschritte_tabelle(
        self, schritte: list[ProzessSchritt]
    ):
        tabelle = baue_standard_tabelle(
            titel="Rezept | Prozessschritte",
            caption="Aktueller Stand",
        )
        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column("Key", style="magenta", max_width=14, overflow="ellipsis")
        tabelle.add_column("Label", style="bold white", max_width=22, overflow="ellipsis")
        tabelle.add_column("Min", style="yellow", justify="right", width=6)
        tabelle.add_column("Temp C", style="green", justify="right", width=8)

        if not schritte:
            tabelle.add_row("-", "-", "Keine Prozessschritte", "-", "-")
            return tabelle

        sichtbare = schritte[:MAX_ZEILEN_STANDARD]
        for index, schritt in enumerate(sichtbare, start=1):
            temp_text = "-" if schritt.target_temp_c is None else f"{schritt.target_temp_c:.1f}"
            tabelle.add_row(
                str(index),
                kuerze_text(schritt.key, 14),
                kuerze_text(schritt.label, 22),
                str(schritt.duration_min),
                temp_text,
            )

        if len(schritte) > MAX_ZEILEN_STANDARD:
            rest = len(schritte) - MAX_ZEILEN_STANDARD
            tabelle.add_row("...", "...", f"... {rest} weitere", "-", "-")

        return tabelle

    def _baue_backprofil_tabelle(
        self, phasen: list[BackProfilPhase]
    ):
        tabelle = baue_standard_tabelle(
            titel="Rezept | Backprofil",
            caption="Aktueller Stand",
        )
        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column("Phase", style="bold white", max_width=22, overflow="ellipsis")
        tabelle.add_column("Min", style="yellow", justify="right", width=6)
        tabelle.add_column("Temp C", style="green", justify="right", width=8)
        tabelle.add_column("Dampf", style="magenta", justify="right", width=7)

        if not phasen:
            tabelle.add_row("-", "Kein Backprofil", "-", "-", "-")
            return tabelle

        sichtbare = phasen[:MAX_ZEILEN_STANDARD]
        for index, phase in enumerate(sichtbare, start=1):
            tabelle.add_row(
                str(index),
                kuerze_text(phase.phase, 22),
                str(phase.duration_min),
                f"{phase.temp_c:.1f}",
                "ja" if phase.steam else "nein",
            )

        if len(phasen) > MAX_ZEILEN_STANDARD:
            rest = len(phasen) - MAX_ZEILEN_STANDARD
            tabelle.add_row("...", f"... {rest} weitere", "-", "-", "-")

        return tabelle
