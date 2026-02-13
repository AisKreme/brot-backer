from __future__ import annotations

import re
import time
from datetime import datetime

from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from Klassenpakete.backvorgang import (
    BackErgebnis,
    Backvorgang,
    BackZiel,
    RezeptSnapshot,
    SchrittDurchlauf,
    ZutatenVerbrauch,
)
from Klassenpakete.brot_rezept import BrotRezept
from Klassenpakete.json_manager import JsonManager
from Klassenpakete.mehl import Mehl
from Klassenpakete.menu import Menu
from Klassenpakete.ui_layout import (
    HIGHLIGHT_STYLE,
    MAX_ZEILEN_KOMPAKT,
    MAX_ZEILEN_STANDARD,
    TERMINAL_ZIEL_BREITE,
    baue_standard_tabelle,
    kuerze_text,
    sichtfenster_indizes,
)


class BackvorgangMenu:
    """
    Untermenue fuer Backvorgaenge.
    Phase-4-MVP:
    - Rezept waehlen
    - Backvorgang anlegen
    - Gefuehrtes Schritt-Tracking optional durchlaufen
    """

    def __init__(self) -> None:
        self.menuePunkte: list[str] = [
            "Neuen Backvorgang anlegen",
            "Laufenden oder pausierten Backvorgang fortsetzen",
            "Zurueck",
        ]
        self.menu: Menu = Menu(menuePunkte=self.menuePunkte)
        self.rezeptManager: JsonManager = JsonManager("daten/brote.json")
        self.backvorgangManager: JsonManager = JsonManager("daten/backvorgaenge.json")
        self.mehlManager: JsonManager = JsonManager("daten/mehle.json")

    def starten(self, navigation, renderer) -> None:
        self.renderer = renderer
        self.navigation = navigation

        while True:
            auswahlIndex = self.menu.anzeigen(navigation, renderer)

            if auswahlIndex == "BACK":
                return

            if not isinstance(auswahlIndex, int):
                return

            ausgewaehlterPunkt: str = self.menuePunkte[auswahlIndex]

            if ausgewaehlterPunkt == "Neuen Backvorgang anlegen":
                self.neuen_backvorgang_anlegen(navigation)
            elif (
                ausgewaehlterPunkt == "Laufenden oder pausierten Backvorgang fortsetzen"
            ):
                self.laufenden_backvorgang_fortsetzen(navigation)
            elif ausgewaehlterPunkt == "Zurueck":
                return

    def neuen_backvorgang_anlegen(self, navigation) -> None:
        rezepte: list[BrotRezept] = [
            rezept
            for rezept in self.rezeptManager.laden(BrotRezept)
            if rezept.status != "archived"
        ]

        if not rezepte:
            with self.renderer.suspended():
                print("\nKeine Rezepte verfuegbar.")
                input("ENTER druecken, um zurueckzukehren...")
            return

        rezept = self._rezept_auswaehlen(rezepte, navigation)
        if rezept is None:
            return

        scale_factor = self._frage_scale_factor()

        datum_default = datetime.now().date().isoformat()
        with self.renderer.suspended():
            datum_eingabe = input(f"Geplantes Backdatum [{datum_default}]: ").strip()
        planned_bake_date = datum_eingabe or datum_default

        bestehende_backvorgaenge = self.backvorgangManager.laden(Backvorgang)
        neuer_backvorgang = self._baue_backvorgang(
            rezept=rezept,
            scale_factor=scale_factor,
            planned_bake_date=planned_bake_date,
            bestehende_backvorgaenge=bestehende_backvorgaenge,
        )

        with self.renderer.suspended():
            zutaten_bearbeiten = (
                input("Zutaten fuer diesen Backvorgang bearbeiten? (j/n) [n]: ")
                .strip()
                .lower()
            )
        if zutaten_bearbeiten in ("j", "ja", "y", "yes"):
            self._zutaten_editor_starten(neuer_backvorgang)

        with self.renderer.suspended():
            tracking_starten = (
                input("Gefuehrtes Schritt-Tracking jetzt starten? (j/n) [j]: ")
                .strip()
                .lower()
            )

        if tracking_starten in ("", "j", "ja", "y", "yes"):
            self._fuehre_schritt_tracking_durch(neuer_backvorgang)

        zeitstempel = self._jetzt_iso()
        neuer_backvorgang.created_at = zeitstempel
        neuer_backvorgang.updated_at = zeitstempel

        bestehende_backvorgaenge.append(neuer_backvorgang)
        self.backvorgangManager.speichern(bestehende_backvorgaenge)

        with self.renderer.suspended():
            print("\nBackvorgang gespeichert.")
            print(f"ID: {neuer_backvorgang.id}")
            print(f"Status: {neuer_backvorgang.status}")
            input("ENTER druecken, um zurueckzukehren...")

    def laufenden_backvorgang_fortsetzen(self, navigation) -> None:
        backvorgaenge = self.backvorgangManager.laden(Backvorgang)
        laufende = [
            eintrag
            for eintrag in backvorgaenge
            if eintrag.status in ("running", "paused", "planned")
            and len(eintrag.step_runs) > 0
        ]

        if not laufende:
            with self.renderer.suspended():
                tabelle = self._baue_fortsetzen_tabelle(laufende)
                self.renderer.console.print(tabelle)
                input("ENTER druecken, um zurueckzukehren...")
            return

        aktueller_index = 0

        def render():
            return self._baue_fortsetzen_tabelle(
                laufende,
                highlight_index=aktueller_index,
            )

        def input_handler(taste: str):
            nonlocal aktueller_index

            if taste == "UP":
                aktueller_index = (aktueller_index - 1) % len(laufende)
                return None
            if taste == "DOWN":
                aktueller_index = (aktueller_index + 1) % len(laufende)
                return None
            if taste == "ENTER":
                return laufende[aktueller_index]
            if taste in ("BACK", "ESC"):
                return taste
            return None

        auswahl = self.renderer.render_loop(render, navigation, input_handler)

        if not isinstance(auswahl, Backvorgang):
            return

        backvorgang = auswahl
        with self.renderer.suspended():
            zutaten_bearbeiten = (
                input("Zutaten fuer diesen Backvorgang bearbeiten? (j/n) [n]: ")
                .strip()
                .lower()
            )
        if zutaten_bearbeiten in ("j", "ja", "y", "yes"):
            self._zutaten_editor_starten(backvorgang)

        self._fuehre_schritt_tracking_durch(backvorgang)
        backvorgang.updated_at = self._jetzt_iso()
        self.backvorgangManager.speichern(backvorgaenge)

        with self.renderer.suspended():
            print("\nBackvorgang aktualisiert.")
            print(f"ID: {backvorgang.id}")
            print(f"Status: {backvorgang.status}")
            input("ENTER druecken, um zurueckzukehren...")

    def _baue_fortsetzen_tabelle(
        self,
        backvorgaenge: list[Backvorgang],
        highlight_index: int | None = None,
    ) -> Table:
        tabelle = baue_standard_tabelle(
            titel="Brot-Backer | Backvorgang fortsetzen",
            caption=(
                "↑ ↓ Navigieren | ENTER Auswahl | BACK Zurueck"
                if backvorgaenge
                else "Keine laufenden, pausierten oder geplanten Backvorgaenge"
            ),
        )
        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column(
            "Rezept",
            style="bold white",
            no_wrap=True,
            overflow="ellipsis",
            max_width=18,
        )
        tabelle.add_column(
            "ID",
            style="magenta",
            no_wrap=True,
            overflow="ellipsis",
            max_width=16,
        )
        tabelle.add_column("Status", style="cyan", no_wrap=True, width=8)
        tabelle.add_column("Offen", style="yellow", justify="right", width=5)
        tabelle.add_column(
            "Start",
            style="green",
            no_wrap=True,
            overflow="ellipsis",
            max_width=14,
        )

        if not backvorgaenge:
            tabelle.add_row(
                "-",
                "Keine fortsetzbaren Backvorgaenge",
                "-",
                "-",
                "-",
                "-",
            )
            return tabelle

        aktive_zeile = highlight_index if highlight_index is not None else 0
        sichtbare, hat_oben, hat_unten = sichtfenster_indizes(
            anzahl_zeilen=len(backvorgaenge),
            aktiver_index=aktive_zeile,
            max_zeilen=MAX_ZEILEN_STANDARD,
        )

        if hat_oben:
            tabelle.add_row("...", "...", "...", "...", "...", "...", style="dim")

        for index in sichtbare:
            eintrag = backvorgaenge[index]
            rezept_name = eintrag.recipe_snapshot.name or eintrag.recipe_id
            start = eintrag.started_at or "-"
            row_style = HIGHLIGHT_STYLE if highlight_index == index else ""
            tabelle.add_row(
                str(index + 1),
                kuerze_text(rezept_name, 18),
                kuerze_text(eintrag.id, 16),
                eintrag.status,
                str(self._zaehle_offene_schritte(eintrag)),
                kuerze_text(start, 14),
                style=row_style,
            )

        if hat_unten:
            tabelle.add_row("...", "...", "...", "...", "...", "...", style="dim")

        return tabelle

    def _rezept_auswaehlen(
        self, rezepte: list[BrotRezept], navigation
    ) -> BrotRezept | None:
        eintraege = [f"{rezept.name} | {rezept.id}" for rezept in rezepte]
        rezept_menu = Menu(eintraege)
        auswahl = rezept_menu.anzeigen(navigation, self.renderer)

        if not isinstance(auswahl, int):
            return None

        return rezepte[auswahl]

    def _frage_scale_factor(self) -> float:
        with self.renderer.suspended():
            roh = input(
                "Scale-Faktor [1.0] (1.0=Original, 0.5=halbe Menge, 2.0=doppelte Menge): "
            ).strip().replace(",", ".")

        if not roh:
            return 1.0

        try:
            wert = float(roh)
        except ValueError:
            with self.renderer.suspended():
                print("Ungueltiger Wert, Scale-Faktor wird auf 1.0 gesetzt.")
            return 1.0

        if wert <= 0:
            with self.renderer.suspended():
                print("Scale-Faktor muss groesser als 0 sein, setze auf 1.0.")
            return 1.0

        return wert

    def _baue_backvorgang(
        self,
        rezept: BrotRezept,
        scale_factor: float,
        planned_bake_date: str,
        bestehende_backvorgaenge: list[Backvorgang],
    ) -> Backvorgang:
        ingredient_usage: list[ZutatenVerbrauch] = [
            ZutatenVerbrauch(
                mehl_id=anteil.mehl_id,
                planned_g=round(anteil.amount_g * scale_factor, 3),
                actual_g=0.0,
                stock_deducted_g=0.0,
            )
            for anteil in rezept.formula.flours
        ]
        gesamt_mehl_g = self._berechne_gesamt_mehlmenge_g(rezept, scale_factor)
        wasser_aus_hydration_g = self._berechne_wasser_aus_hydration_g(
            rezept,
            scale_factor,
            gesamt_mehl_g,
        )
        if wasser_aus_hydration_g > 0:
            ingredient_usage.append(
                ZutatenVerbrauch(
                    mehl_id="wasser",
                    planned_g=wasser_aus_hydration_g,
                    actual_g=0.0,
                    stock_deducted_g=0.0,
                )
            )

        step_runs: list[SchrittDurchlauf] = [
            SchrittDurchlauf(
                key=schritt.key,
                label=schritt.label,
                planned_duration_min=schritt.duration_min,
                actual_start_at=None,
                actual_end_at=None,
                actual_duration_min=None,
                avg_temp_c=None,
                note="",
            )
            for schritt in rezept.process_template
        ]

        loaf_count = max(
            1, int(round(rezept.yield_data.loaf_count_default * scale_factor))
        )
        zielgewicht = round(rezept.yield_data.target_dough_weight_g * scale_factor, 3)

        return Backvorgang(
            id=self._generiere_backvorgang_id(bestehende_backvorgaenge),
            recipe_id=rezept.id,
            recipe_version=rezept.version,
            recipe_snapshot=RezeptSnapshot(
                name=rezept.name,
                hydration_percent=rezept.targets.hydration_percent,
            ),
            status="planned",
            planned_bake_date=planned_bake_date,
            started_at=None,
            ended_at=None,
            scale_factor=scale_factor,
            target=BackZiel(loaf_count=loaf_count, target_dough_weight_g=zielgewicht),
            ingredient_usage=ingredient_usage,
            step_runs=step_runs,
            measurements=[],
            outcome=BackErgebnis(),
            issues=[],
            notes="",
            attachments=[],
            custom={
                "hydration_percent_used": rezept.targets.hydration_percent,
                "flour_total_planned_g": gesamt_mehl_g,
                "hydration_water_planned_g": wasser_aus_hydration_g,
            },
        )

    def _berechne_gesamt_mehlmenge_g(
        self,
        rezept: BrotRezept,
        scale_factor: float,
    ) -> float:
        return round(
            sum(max(0.0, anteil.amount_g) * scale_factor for anteil in rezept.formula.flours),
            3,
        )

    def _berechne_wasser_aus_hydration_g(
        self,
        rezept: BrotRezept,
        scale_factor: float,
        gesamt_mehl_g: float,
    ) -> float:
        hydration = rezept.targets.hydration_percent
        if hydration > 0 and gesamt_mehl_g > 0:
            return round(gesamt_mehl_g * (hydration / 100.0), 3)

        # Fallback fuer Rezepte ohne valide Hydration
        return round(max(0.0, rezept.formula.water_g) * scale_factor, 3)

    def _fuehre_schritt_tracking_durch(self, backvorgang: Backvorgang) -> None:
        if not backvorgang.step_runs:
            with self.renderer.suspended():
                print("\nDieses Rezept hat keine Prozessschritte.")
            backvorgang.status = "planned"
            return

        rezept = self._hole_rezept(backvorgang.recipe_id)
        with self.renderer.suspended():
            hilfe_anzeigen = (
                input("Rezeptuebersicht und Backhinweise anzeigen? (j/n) [j]: ")
                .strip()
                .lower()
            )
        if hilfe_anzeigen in ("", "j", "ja", "y", "yes"):
            self._zeige_rezept_uebersicht(backvorgang, rezept)

        offene_schritte = [
            schritt
            for schritt in backvorgang.step_runs
            if schritt.actual_end_at is None and schritt.actual_duration_min is None
        ]

        if not offene_schritte:
            with self.renderer.suspended():
                abschliessen = (
                    input(
                        "\nKeine offenen Schritte mehr. Backvorgang als completed abschliessen? (j/n) [j]: "
                    )
                    .strip()
                    .lower()
                )
            if abschliessen in ("", "j", "ja", "y", "yes"):
                self._finalisiere_backvorgang(backvorgang)
            return

        for index, schritt in enumerate(offene_schritte, start=1):
            while True:
                with self.renderer.suspended():
                    print("\n" + "-" * 60)
                    print(f"\nSchritt {index}/{len(offene_schritte)}")
                    print(f"{schritt.label or schritt.key} ({schritt.key})")
                    print(f"Geplante Dauer: {schritt.planned_duration_min} Min.")
                    self._zeige_schritt_hilfe(rezept, schritt.key)
                    aktion = input(
                        "ENTER Schritt starten (Timer startet automatisch) | p pausieren: "
                    ).strip().lower()

                if aktion == "":
                    break

                if aktion == "p":
                    if backvorgang.started_at is not None:
                        backvorgang.status = "paused"
                    else:
                        backvorgang.status = "planned"
                    return

                with self.renderer.suspended():
                    print("Ungueltige Eingabe. Bitte nur ENTER oder p verwenden.")
                    input("ENTER fuer erneute Eingabe...")

            start_dt = datetime.now().astimezone()
            if backvorgang.started_at is None:
                backvorgang.started_at = start_dt.isoformat(timespec="seconds")
            backvorgang.status = "running"
            schritt.actual_start_at = start_dt.isoformat(timespec="seconds")

            with self.renderer.suspended():
                self.renderer.console.clear()

            timer_result = self._starte_timer_live(
                backvorgang=backvorgang,
                schritt=schritt,
                rezept=rezept,
                schritt_index=index,
                schritt_gesamt=len(offene_schritte),
            )
            if timer_result != "completed":
                return

            ende_dt = datetime.now().astimezone()
            schritt.actual_end_at = ende_dt.isoformat(timespec="seconds")

            dauer_min = int(round((ende_dt - start_dt).total_seconds() / 60))
            schritt.actual_duration_min = max(1, dauer_min)

            with self.renderer.suspended():
                temp_roh = input("Durchschnittstemperatur in C (optional): ").strip()
                note = input("Notiz zu diesem Schritt (optional): ").strip()

            schritt.avg_temp_c = self._parse_float_oder_none(temp_roh)
            if note:
                schritt.note = note

        self._finalisiere_backvorgang(backvorgang)

    def _zeige_tracking_checkpoint(
        self,
        backvorgang: Backvorgang,
        aktiver_schritt_key: str | None = None,
        rezept: BrotRezept | None = None,
    ) -> None:
        schritte_tabelle = self._baue_tracking_checkpoint_tabelle(
            backvorgang=backvorgang,
            aktiver_schritt_key=aktiver_schritt_key,
            rezept=rezept,
        )
        self.renderer.console.print(schritte_tabelle)

    def _baue_tracking_checkpoint_tabelle(
        self,
        backvorgang: Backvorgang,
        aktiver_schritt_key: str | None = None,
        rezept: BrotRezept | None = None,
    ) -> Table:
        offene = self._zaehle_offene_schritte(backvorgang)
        erledigt = len(backvorgang.step_runs) - offene
        name = backvorgang.recipe_snapshot.name or backvorgang.recipe_id

        schritte_tabelle = baue_standard_tabelle(
            titel=(
                "Tracking | "
                f"{kuerze_text(name, 16)} | {backvorgang.status} | "
                f"offen {offene} / erledigt {erledigt}"
            ),
        )
        schritte_tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        schritte_tabelle.add_column(
            "Schritt",
            style="bold white",
            no_wrap=True,
            overflow="ellipsis",
            max_width=22,
        )
        schritte_tabelle.add_column("Status", style="magenta", no_wrap=True, width=11)
        schritte_tabelle.add_column("Soll", style="green", justify="right", width=6)
        schritte_tabelle.add_column("Ist", style="yellow", justify="right", width=6)

        aktive_position = self._aktive_schritt_position(
            backvorgang.step_runs, aktiver_schritt_key
        )
        fenster, hat_oben, hat_unten = self._schritt_fenster(
            backvorgang.step_runs,
            aktive_position,
            max_rows=MAX_ZEILEN_KOMPAKT,
        )

        if hat_oben:
            schritte_tabelle.add_row("...", "...", "...", "...", "...", style="dim")

        for index in fenster:
            schritt = backvorgang.step_runs[index]
            ist_aktiv = aktiver_schritt_key == schritt.key
            status_text = self._status_text_fuer_schritt(schritt, ist_aktiv)
            ist_text = (
                "-"
                if schritt.actual_duration_min is None
                else str(schritt.actual_duration_min)
            )
            row_style = "bold black on bright_yellow" if ist_aktiv else ""

            schritte_tabelle.add_row(
                str(index + 1),
                schritt.label or schritt.key,
                status_text,
                str(schritt.planned_duration_min),
                ist_text,
                style=row_style,
            )

        if hat_unten:
            schritte_tabelle.add_row("...", "...", "...", "...", "...", style="dim")

        return schritte_tabelle

    def _status_text_fuer_schritt(
        self, schritt: SchrittDurchlauf, ist_aktiv: bool
    ) -> str:
        if ist_aktiv:
            return "[black on bright_yellow]aktuell[/black on bright_yellow]"

        if schritt.actual_duration_min == 0 or schritt.note == "Uebersprungen.":
            return "[yellow]uebersprungen[/yellow]"

        if schritt.actual_end_at is not None or (
            schritt.actual_duration_min is not None and schritt.actual_duration_min > 0
        ):
            return "[green]erledigt[/green]"

        if schritt.actual_start_at is not None and schritt.actual_end_at is None:
            return "[cyan]in Arbeit[/cyan]"

        return "[white]offen[/white]"

    def _baue_zutaten_tabelle(
        self,
        zutaten: list[ZutatenVerbrauch],
        title: str,
        max_rows: int = 8,
    ) -> Table:
        tabelle = baue_standard_tabelle(
            titel=title,
        )
        tabelle.add_column(
            "Zutat",
            style="bold white",
            no_wrap=True,
            overflow="ellipsis",
            max_width=24,
        )
        tabelle.add_column("Soll g", style="green", justify="right", width=8)
        tabelle.add_column("Ist g", style="yellow", justify="right", width=8)
        tabelle.add_column("Abzug g", style="magenta", justify="right", width=9)

        if not zutaten:
            tabelle.add_row("-", "-", "-", "-")
            return tabelle

        sichtbare = zutaten[:max_rows]
        for eintrag in sichtbare:
            tabelle.add_row(
                kuerze_text(eintrag.mehl_id or "-", 24),
                f"{eintrag.planned_g:.1f}",
                f"{eintrag.actual_g:.1f}",
                f"{eintrag.stock_deducted_g:.1f}",
            )

        if len(zutaten) > max_rows:
            rest = len(zutaten) - max_rows
            tabelle.add_row(
                f"... {rest} weitere",
                "-",
                "-",
                "-",
                style="dim",
            )

        return tabelle

    def _zutaten_editor_starten(self, backvorgang: Backvorgang) -> None:
        while True:
            with self.renderer.suspended():
                self.renderer.console.print(
                    self._baue_zutaten_editor_tabelle(backvorgang.ingredient_usage)
                )
                print(
                    "\nAktion: [a] Zutat hinzufuegen | [b] Zutat bearbeiten | "
                    "[d] Zutat loeschen | [s] Ist=Soll fuer alle | [q] fertig"
                )
                aktion = input("Auswahl: ").strip().lower()

            if aktion in ("q", ""):
                self._synchronisiere_custom_nach_zutaten_aenderung(backvorgang)
                return
            if aktion == "a":
                self._zutat_hinzufuegen(backvorgang)
            elif aktion == "b":
                self._zutat_bearbeiten(backvorgang)
            elif aktion == "d":
                self._zutat_loeschen(backvorgang)
            elif aktion == "s":
                self._setze_ist_auf_soll(backvorgang)

    def _baue_zutaten_editor_tabelle(
        self,
        zutaten: list[ZutatenVerbrauch],
    ) -> Table:
        tabelle = baue_standard_tabelle(
            titel="Zutaten-Editor | ingredient_usage",
            caption="ENTER nach jeder Eingabe bestaetigen",
        )
        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column(
            "Zutat",
            style="bold white",
            no_wrap=True,
            overflow="ellipsis",
            max_width=20,
        )
        tabelle.add_column("Soll g", style="green", justify="right", width=8)
        tabelle.add_column("Ist g", style="yellow", justify="right", width=8)
        tabelle.add_column("Abzug g", style="magenta", justify="right", width=8)

        if not zutaten:
            tabelle.add_row("-", "Keine Zutaten vorhanden", "-", "-", "-")
            return tabelle

        sichtbare = zutaten[:MAX_ZEILEN_STANDARD]
        for index, eintrag in enumerate(sichtbare, start=1):
            tabelle.add_row(
                str(index),
                kuerze_text(eintrag.mehl_id or "-", 20),
                f"{eintrag.planned_g:.1f}",
                f"{eintrag.actual_g:.1f}",
                f"{eintrag.stock_deducted_g:.1f}",
            )

        if len(zutaten) > MAX_ZEILEN_STANDARD:
            rest = len(zutaten) - MAX_ZEILEN_STANDARD
            tabelle.add_row("...", f"... {rest} weitere", "-", "-", "-")

        return tabelle

    def _zutat_hinzufuegen(self, backvorgang: Backvorgang) -> None:
        with self.renderer.suspended():
            print("\nNeue Zutat fuer ingredient_usage")
            mehl_id = input("Zutat-ID (z.B. mehl_weizen_550 oder wasser): ").strip()
            planned_roh = input("Soll g [0]: ").strip()
            actual_roh = input("Ist g [0]: ").strip()
            stock_roh = input("Abzug g [Ist]: ").strip()

        if not mehl_id:
            return

        planned = self._parse_float_oder_none(planned_roh)
        actual = self._parse_float_oder_none(actual_roh)
        stock = self._parse_float_oder_none(stock_roh)

        planned_g = round(max(0.0, planned if planned is not None else 0.0), 3)
        actual_g = round(max(0.0, actual if actual is not None else 0.0), 3)
        stock_deducted_g = (
            round(max(0.0, stock), 3) if stock is not None else round(actual_g, 3)
        )

        backvorgang.ingredient_usage.append(
            ZutatenVerbrauch(
                mehl_id=mehl_id,
                planned_g=planned_g,
                actual_g=actual_g,
                stock_deducted_g=stock_deducted_g,
            )
        )

    def _zutat_bearbeiten(self, backvorgang: Backvorgang) -> None:
        if not backvorgang.ingredient_usage:
            return

        with self.renderer.suspended():
            index_roh = input("Zutat-Nr. zum Bearbeiten: ").strip()

        index = self._parse_int_oder_none(index_roh)
        if index is None or not (1 <= index <= len(backvorgang.ingredient_usage)):
            return

        eintrag = backvorgang.ingredient_usage[index - 1]
        with self.renderer.suspended():
            mehl_id = input(f"Zutat-ID [{eintrag.mehl_id}]: ").strip()
            planned_roh = input(f"Soll g [{eintrag.planned_g}]: ").strip()
            actual_roh = input(f"Ist g [{eintrag.actual_g}]: ").strip()
            stock_roh = input(f"Abzug g [{eintrag.stock_deducted_g}]: ").strip()

        if mehl_id:
            eintrag.mehl_id = mehl_id

        planned = self._parse_float_oder_none(planned_roh)
        if planned is not None:
            eintrag.planned_g = round(max(0.0, planned), 3)

        actual = self._parse_float_oder_none(actual_roh)
        if actual is not None:
            eintrag.actual_g = round(max(0.0, actual), 3)

        stock = self._parse_float_oder_none(stock_roh)
        if stock is not None:
            eintrag.stock_deducted_g = round(max(0.0, stock), 3)

    def _zutat_loeschen(self, backvorgang: Backvorgang) -> None:
        if not backvorgang.ingredient_usage:
            return

        with self.renderer.suspended():
            index_roh = input("Zutat-Nr. zum Loeschen: ").strip()

        index = self._parse_int_oder_none(index_roh)
        if index is None or not (1 <= index <= len(backvorgang.ingredient_usage)):
            return

        del backvorgang.ingredient_usage[index - 1]

    def _setze_ist_auf_soll(self, backvorgang: Backvorgang) -> None:
        for eintrag in backvorgang.ingredient_usage:
            eintrag.actual_g = round(max(0.0, eintrag.planned_g), 3)
            eintrag.stock_deducted_g = round(max(0.0, eintrag.actual_g), 3)

    def _synchronisiere_custom_nach_zutaten_aenderung(
        self, backvorgang: Backvorgang
    ) -> None:
        flour_total = round(
            sum(
                max(0.0, eintrag.planned_g)
                for eintrag in backvorgang.ingredient_usage
                if (eintrag.mehl_id or "").lower() != "wasser"
            ),
            3,
        )
        water = round(self._geplante_wassermenge_g(backvorgang), 3)
        backvorgang.custom["flour_total_planned_g"] = flour_total
        backvorgang.custom["hydration_water_planned_g"] = water

    def _aktive_schritt_position(
        self, schritte: list[SchrittDurchlauf], aktiver_key: str | None
    ) -> int:
        if not schritte:
            return 0
        if aktiver_key is None:
            return 0
        for index, schritt in enumerate(schritte):
            if schritt.key == aktiver_key:
                return index
        return 0

    def _schritt_fenster(
        self, schritte: list[SchrittDurchlauf], aktive_position: int, max_rows: int = 6
    ) -> tuple[list[int], bool, bool]:
        return sichtfenster_indizes(
            anzahl_zeilen=len(schritte),
            aktiver_index=aktive_position,
            max_zeilen=max_rows,
        )

    def _geplante_wassermenge_g(self, backvorgang: Backvorgang) -> float:
        for eintrag in backvorgang.ingredient_usage:
            if (eintrag.mehl_id or "").lower() == "wasser":
                return round(max(0.0, eintrag.planned_g), 3)

        # Fallback fuer Altbestaende, falls Wasser noch nicht als Zutat gepflegt wurde
        wasser_custom = backvorgang.custom.get("hydration_water_planned_g")
        if isinstance(wasser_custom, (int, float)):
            return round(max(0.0, float(wasser_custom)), 3)

        hydration = backvorgang.recipe_snapshot.hydration_percent
        mehl_summe = sum(
            max(0.0, eintrag.planned_g)
            for eintrag in backvorgang.ingredient_usage
            if (eintrag.mehl_id or "").lower() != "wasser"
        )
        if hydration is not None and hydration > 0 and mehl_summe > 0:
            return round(mehl_summe * (hydration / 100.0), 3)
        return 0.0

    def _hole_rezept(self, rezept_id: str) -> BrotRezept | None:
        rezepte = self.rezeptManager.laden(BrotRezept)
        for rezept in rezepte:
            if rezept.id == rezept_id:
                return rezept
        return None

    def _zeige_rezept_uebersicht(
        self, backvorgang: Backvorgang, rezept: BrotRezept | None
    ) -> None:
        with self.renderer.suspended():
            titel = backvorgang.recipe_snapshot.name or backvorgang.recipe_id
            hydration_text = (
                f"{backvorgang.recipe_snapshot.hydration_percent}%"
                if backvorgang.recipe_snapshot.hydration_percent is not None
                else "-"
            )
            wasser_text = f"{self._geplante_wassermenge_g(backvorgang):.1f}g"
            summary = Panel(
                (
                    f"[bold]Rezept:[/bold] {kuerze_text(titel, 42)}\n"
                    f"[bold]ID:[/bold] {kuerze_text(backvorgang.id, 26)}   "
                    f"[bold]Scale:[/bold] {backvorgang.scale_factor}   "
                    f"[bold]Hydration:[/bold] {hydration_text}\n"
                    f"[bold]Wasser (Hydration):[/bold] {wasser_text}\n"
                    f"[bold]Ziel:[/bold] {backvorgang.target.loaf_count} Laib(e), "
                    f"{backvorgang.target.target_dough_weight_g}g Teig"
                ),
                title="[bold bright_white]Backvorgang Uebersicht[/bold bright_white]",
                border_style="grey50",
                width=TERMINAL_ZIEL_BREITE,
            )

            mehl_tabelle = self._baue_zutaten_tabelle(
                backvorgang.ingredient_usage,
                title="Zutatenmengen (Mehl + Wasser)",
                max_rows=MAX_ZEILEN_KOMPAKT,
            )

            self.renderer.console.print(Group(summary, mehl_tabelle))

            self._zeige_optionale_rezept_details(backvorgang, rezept)
            input("\nENTER druecken, um mit dem Tracking zu starten...")

    def _zeige_optionale_rezept_details(
        self, backvorgang: Backvorgang, rezept: BrotRezept | None
    ) -> None:
        if rezept is None:
            return

        hat_zusatz = len(rezept.formula.additional_ingredients) > 0
        hat_backprofil = len(rezept.bake_profile) > 0
        hat_notiz = bool(rezept.notes.strip())

        if not (hat_zusatz or hat_backprofil or hat_notiz):
            return

        detail_antwort = (
            input("Weitere Rezept-Details anzeigen? (j/n) [n]: ").strip().lower()
        )
        if detail_antwort not in ("j", "ja", "y", "yes"):
            return

        renderables = []
        if hat_zusatz:
            renderables.append(
                self._baue_zusatz_tabelle(
                    rezept=rezept,
                    scale_factor=backvorgang.scale_factor,
                    max_rows=MAX_ZEILEN_KOMPAKT,
                )
            )
        if hat_backprofil:
            renderables.append(
                self._baue_backprofil_tabelle(
                    rezept=rezept,
                    max_rows=MAX_ZEILEN_KOMPAKT,
                )
            )
        if hat_notiz:
            renderables.append(
                Panel(
                    kuerze_text(rezept.notes, 220),
                    title="[bold bright_white]Rezept-Notiz[/bold bright_white]",
                    border_style="grey50",
                    width=TERMINAL_ZIEL_BREITE,
                )
            )

        if renderables:
            self.renderer.console.print(Group(*renderables))

    def _baue_zusatz_tabelle(
        self,
        rezept: BrotRezept,
        scale_factor: float,
        max_rows: int = MAX_ZEILEN_KOMPAKT,
    ) -> Table:
        tabelle = baue_standard_tabelle(
            titel="Weitere Zutaten (skaliert)",
        )
        tabelle.add_column(
            "Zutat",
            style="bold white",
            overflow="ellipsis",
            no_wrap=True,
            max_width=24,
        )
        tabelle.add_column("Menge", style="yellow", justify="right", width=10)
        tabelle.add_column("Einheit", style="green", justify="right", width=8)

        if not rezept.formula.additional_ingredients:
            tabelle.add_row("-", "-", "-")
            return tabelle

        sichtbare = rezept.formula.additional_ingredients[:max_rows]
        for zusatz in sichtbare:
            menge = round(zusatz.amount_g * scale_factor, 3)
            tabelle.add_row(
                kuerze_text(zusatz.name, 24),
                str(menge),
                zusatz.unit or "g",
            )

        if len(rezept.formula.additional_ingredients) > max_rows:
            rest = len(rezept.formula.additional_ingredients) - max_rows
            tabelle.add_row("...", f"+{rest}", "-", style="dim")

        return tabelle

    def _baue_backprofil_tabelle(
        self,
        rezept: BrotRezept,
        max_rows: int = MAX_ZEILEN_KOMPAKT,
    ) -> Table:
        tabelle = baue_standard_tabelle(
            titel="Backprofil",
        )
        tabelle.add_column(
            "Phase", style="bold white", max_width=22, overflow="ellipsis"
        )
        tabelle.add_column("Min", style="yellow", justify="right", width=6)
        tabelle.add_column("Temp C", style="cyan", justify="right", width=7)
        tabelle.add_column("Dampf", style="magenta", justify="right", width=7)

        if not rezept.bake_profile:
            tabelle.add_row("-", "-", "-", "-")
            return tabelle

        sichtbare = rezept.bake_profile[:max_rows]
        for phase in sichtbare:
            tabelle.add_row(
                kuerze_text(phase.phase, 22),
                str(phase.duration_min),
                str(phase.temp_c),
                "ja" if phase.steam else "nein",
            )

        if len(rezept.bake_profile) > max_rows:
            rest = len(rezept.bake_profile) - max_rows
            tabelle.add_row("...", f"+{rest}", "-", "-", style="dim")

        return tabelle

    def _zeige_schritt_hilfe(self, rezept: BrotRezept | None, schritt_key: str) -> None:
        if rezept is None:
            return

        passende_schritte = [
            schritt for schritt in rezept.process_template if schritt.key == schritt_key
        ]
        if passende_schritte:
            schritt = passende_schritte[0]
            if schritt.target_temp_c is not None:
                print(f"Zieltemperatur: {schritt.target_temp_c}C")

        if schritt_key == "backen" and rezept.bake_profile:
            print("Backphasen:")
            for phase in rezept.bake_profile:
                dampf = "Dampf" if phase.steam else "kein Dampf"
                print(
                    f"- {phase.phase}: {phase.duration_min} Min. bei {phase.temp_c}C ({dampf})"
                )

    def _abbrechen_backvorgang(self, backvorgang: Backvorgang) -> bool:
        with self.renderer.suspended():
            bestaetigung = (
                input("Backvorgang wirklich abbrechen? (j/n) [n]: ").strip().lower()
            )

        if bestaetigung not in ("j", "ja", "y", "yes"):
            return False

        if backvorgang.started_at is not None:
            backvorgang.ended_at = self._jetzt_iso()
        backvorgang.status = "aborted"

        with self.renderer.suspended():
            notiz = input("Abbruchgrund (optional): ").strip()
        if notiz:
            if backvorgang.notes:
                backvorgang.notes += f"\nAbbruch: {notiz}"
            else:
                backvorgang.notes = f"Abbruch: {notiz}"

        return True

    def _baue_timer_footer_panel(
        self,
        schritt: SchrittDurchlauf,
        schritt_index: int,
        schritt_gesamt: int,
        verbleibende_sekunden: int,
        timer_fertig: bool = False,
    ) -> Panel:
        minuten, sekunden = divmod(max(0, verbleibende_sekunden), 60)
        timer_text = f"{minuten:02d}:{sekunden:02d}"

        if timer_fertig:
            status = "[bold red]Timer abgelaufen[/bold red]"
            border = "red"
        elif verbleibende_sekunden <= 60:
            status = "[bold yellow]Timer laeuft[/bold yellow]"
            border = "yellow"
        else:
            status = "[bold green]Timer laeuft[/bold green]"
            border = "green"

        text = (
            f"[bold]Schritt {schritt_index}/{schritt_gesamt}:[/bold] "
            f"{kuerze_text(schritt.label or schritt.key, 40)}\n"
            f"[bold]Restzeit:[/bold] {timer_text}   [bold]Status:[/bold] {status}\n"
            "[dim]ENTER Schritt beenden | p Backvorgang pausieren[/dim]"
        )
        return Panel(
            text,
            title="[bold bright_white]Timer-Status[/bold bright_white]",
            border_style=border,
            width=TERMINAL_ZIEL_BREITE,
        )

    def _starte_timer_live(
        self,
        backvorgang: Backvorgang,
        schritt: SchrittDurchlauf,
        rezept: BrotRezept | None,
        schritt_index: int,
        schritt_gesamt: int,
    ) -> str:
        if schritt.planned_duration_min <= 0:
            with self.renderer.suspended():
                print("Kein Timer gestartet (geplante Dauer <= 0).")
            return "completed"

        endzeit = time.monotonic() + int(schritt.planned_duration_min * 60)
        alarm_gesendet = False

        while True:
            rest = max(0, int(round(endzeit - time.monotonic())))
            timer_fertig = rest <= 0

            tracking_tabelle = self._baue_tracking_checkpoint_tabelle(
                backvorgang=backvorgang,
                aktiver_schritt_key=schritt.key,
                rezept=rezept,
            )
            footer = self._baue_timer_footer_panel(
                schritt=schritt,
                schritt_index=schritt_index,
                schritt_gesamt=schritt_gesamt,
                verbleibende_sekunden=rest,
                timer_fertig=timer_fertig,
            )
            self.renderer.update(Group(tracking_tabelle, footer))

            if timer_fertig and not alarm_gesendet:
                self.renderer.console.bell()
                alarm_gesendet = True
                return "completed"

            taste = self.navigation.lese_taste_mit_timeout(0.25)
            if taste is None:
                continue

            if taste == "ENTER":
                return "completed"

            if taste == "p":
                backvorgang.status = "paused"
                return "paused"

    def _finalisiere_backvorgang(self, backvorgang: Backvorgang) -> None:
        backvorgang.status = "completed"
        if backvorgang.started_at is None:
            backvorgang.started_at = self._jetzt_iso()
        backvorgang.ended_at = self._jetzt_iso()

        self._erfasse_ingredient_usage(backvorgang)
        self._erfasse_outcome(backvorgang)
        self._ziehe_mehlbestand_ab(backvorgang)

    def _erfasse_ingredient_usage(self, backvorgang: Backvorgang) -> None:
        if not backvorgang.ingredient_usage:
            return

        with self.renderer.suspended():
            uebernehmen = (
                input(
                    "Soll geplante Mehlmenge als Ist-Verbrauch uebernommen werden? (j/n) [j]: "
                )
                .strip()
                .lower()
            )

        if uebernehmen in ("", "j", "ja", "y", "yes"):
            for eintrag in backvorgang.ingredient_usage:
                eintrag.actual_g = round(eintrag.planned_g, 3)
                eintrag.stock_deducted_g = round(eintrag.actual_g, 3)
            return

        for eintrag in backvorgang.ingredient_usage:
            default = str(round(eintrag.planned_g, 3))
            with self.renderer.suspended():
                roh = input(
                    f"Ist-Verbrauch fuer {eintrag.mehl_id} in g [{default}]: "
                ).strip()

            if roh:
                wert = self._parse_float_oder_none(roh)
                eintrag.actual_g = (
                    round(wert, 3) if wert is not None else round(eintrag.planned_g, 3)
                )
            else:
                eintrag.actual_g = round(eintrag.planned_g, 3)

            eintrag.stock_deducted_g = round(eintrag.actual_g, 3)

    def _erfasse_outcome(self, backvorgang: Backvorgang) -> None:
        with self.renderer.suspended():
            print("\nAbschlussdaten (optional):")
            rating_roh = input("Bewertung 1-5: ").strip()
            crumb = input("Krume: ").strip()
            crust = input("Kruste: ").strip()
            volume = input("Volumen: ").strip()
            taste_note = input("Geschmacksnotiz: ").strip()
            notes = input("Notizen zum Backvorgang: ").strip()

        if rating_roh.isdigit():
            rating_int = int(rating_roh)
            if 1 <= rating_int <= 5:
                backvorgang.outcome.rating = rating_int

        if crumb:
            backvorgang.outcome.crumb = crumb
        if crust:
            backvorgang.outcome.crust = crust
        if volume:
            backvorgang.outcome.volume = volume
        if taste_note:
            backvorgang.outcome.taste_note = taste_note
        if notes:
            backvorgang.notes = notes

    def _ziehe_mehlbestand_ab(self, backvorgang: Backvorgang) -> None:
        if backvorgang.custom.get("stock_deducted") is True:
            with self.renderer.suspended():
                print("\nMehlbestand wurde fuer diesen Backvorgang bereits abgebucht.")
            return

        mehle = self.mehlManager.laden(Mehl)
        mehle_index = {mehl.id: mehl for mehl in mehle if mehl.id}

        aenderungen: list[str] = []
        fehlende_ids: list[str] = []

        for eintrag in backvorgang.ingredient_usage:
            mehl = mehle_index.get(eintrag.mehl_id)
            if mehl is None:
                if eintrag.mehl_id and eintrag.mehl_id not in ("wasser",):
                    fehlende_ids.append(eintrag.mehl_id)
                continue

            zielmenge = (
                eintrag.stock_deducted_g
                if eintrag.stock_deducted_g > 0
                else eintrag.actual_g
            )
            abzuziehen = int(round(max(0.0, zielmenge)))
            if abzuziehen <= 0:
                continue

            alt = mehl.vorhandenGramm
            neu = max(0, alt - abzuziehen)
            mehl.vorhandenGramm = neu
            mehl.vorhanden = neu > 0
            aenderungen.append(f"- {mehl.id}: {alt}g -> {neu}g (-{abzuziehen}g)")

        if aenderungen:
            self.mehlManager.speichern(mehle)
            backvorgang.custom["stock_deducted"] = True
            backvorgang.custom["stock_deducted_at"] = self._jetzt_iso()
        else:
            backvorgang.custom["stock_deducted"] = False

        if fehlende_ids:
            backvorgang.custom["stock_missing_ids"] = sorted(set(fehlende_ids))

        with self.renderer.suspended():
            if aenderungen:
                print("\nMehlbestand aktualisiert:")
                for zeile in aenderungen:
                    print(zeile)
            else:
                print("\nKeine Mehl-Abbuchung notwendig.")

            if fehlende_ids:
                print("Nicht im Bestand gefuehrt:")
                for mehl_id in sorted(set(fehlende_ids)):
                    print(f"- {mehl_id}")

    def _zaehle_offene_schritte(self, backvorgang: Backvorgang) -> int:
        return sum(
            1
            for schritt in backvorgang.step_runs
            if schritt.actual_end_at is None and schritt.actual_duration_min is None
        )

    def _generiere_backvorgang_id(
        self, bestehende_backvorgaenge: list[Backvorgang]
    ) -> str:
        datumsteil = datetime.now().strftime("%Y_%m_%d")
        praefix = f"bv_{datumsteil}_"
        regex = re.compile(rf"^{re.escape(praefix)}(\d{{3}})$")

        hoechster_index = 0
        for eintrag in bestehende_backvorgaenge:
            match = regex.match(eintrag.id)
            if match:
                hoechster_index = max(hoechster_index, int(match.group(1)))

        return f"{praefix}{hoechster_index + 1:03d}"

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

    def _jetzt_iso(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
