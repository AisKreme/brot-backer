from __future__ import annotations

from rich.table import Table

from Klassenpakete.backvorgang import Backvorgang
from Klassenpakete.json_manager import JsonManager
from Klassenpakete.menu import Menu
from Klassenpakete.ui_layout import MAX_ZEILEN_STANDARD, baue_standard_tabelle, kuerze_text


class DatenMenu:
    """
    Kleines Untermenue fuer Datenansichten.
    """

    def __init__(self) -> None:
        self.menuePunkte: list[str] = [
            "Laufende und pausierte Backvorgaenge anzeigen",
            "Zurueck",
        ]
        self.menu: Menu = Menu(menuePunkte=self.menuePunkte)
        self.backvorgangManager: JsonManager = JsonManager("daten/backvorgaenge.json")

    def starten(self, navigation, renderer) -> None:
        self.renderer = renderer

        while True:
            auswahlIndex = self.menu.anzeigen(navigation, renderer)

            if auswahlIndex == "BACK":
                return

            if not isinstance(auswahlIndex, int):
                return

            ausgewaehlterPunkt: str = self.menuePunkte[auswahlIndex]

            if ausgewaehlterPunkt == "Laufende und pausierte Backvorgaenge anzeigen":
                self.laufende_backvorgaenge_anzeigen(navigation)
            elif ausgewaehlterPunkt == "Zurueck":
                return

    def laufende_backvorgaenge_anzeigen(self, navigation) -> None:
        backvorgaenge = self.backvorgangManager.laden(Backvorgang)
        laufende = [
            eintrag
            for eintrag in backvorgaenge
            if eintrag.status in ("running", "paused")
        ]

        def render():
            tabelle = baue_standard_tabelle(
                titel="Brot-Backer | Laufende/Pausierte Backvorgaenge",
                caption="ENTER oder BACK fuer Zurueck",
            )
            tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
            tabelle.add_column(
                "Rezept",
                style="bold white",
                overflow="ellipsis",
                no_wrap=True,
                max_width=18,
            )
            tabelle.add_column(
                "ID",
                style="magenta",
                overflow="ellipsis",
                no_wrap=True,
                max_width=16,
            )
            tabelle.add_column("Status", style="cyan", width=8)
            tabelle.add_column(
                "Start",
                style="green",
                overflow="ellipsis",
                no_wrap=True,
                max_width=14,
            )
            tabelle.add_column("Offen", style="bold yellow", justify="right", width=5)

            if not laufende:
                tabelle.add_row(
                    "-",
                    "Keine laufenden/pausierten Backvorgaenge",
                    "-",
                    "-",
                    "-",
                    "-",
                )
                return tabelle

            sichtbare = laufende[:MAX_ZEILEN_STANDARD]
            for index, eintrag in enumerate(sichtbare, start=1):
                rezept_name = eintrag.recipe_snapshot.name or eintrag.recipe_id
                start = eintrag.started_at or "-"
                offene_schritte = self._zaehle_offene_schritte(eintrag)
                tabelle.add_row(
                    str(index),
                    kuerze_text(rezept_name, 18),
                    kuerze_text(eintrag.id, 16),
                    eintrag.status,
                    kuerze_text(start, 14),
                    str(offene_schritte),
                )

            if len(laufende) > MAX_ZEILEN_STANDARD:
                rest = len(laufende) - MAX_ZEILEN_STANDARD
                tabelle.add_row("...", f"... {rest} weitere", "-", "-", "-")

            return tabelle

        def input_handler(taste: str):
            if taste in ("BACK", "ENTER", "ESC"):
                return taste
            return None

        self.renderer.render_loop(render, navigation, input_handler)

    def _zaehle_offene_schritte(self, backvorgang: Backvorgang) -> int:
        return sum(
            1
            for schritt in backvorgang.step_runs
            if schritt.actual_end_at is None and schritt.actual_duration_min is None
        )
