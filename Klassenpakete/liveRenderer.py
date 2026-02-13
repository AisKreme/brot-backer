from contextlib import contextmanager
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table

from Klassenpakete.mehl import Mehl
from Klassenpakete.navigation import Navigation
from Klassenpakete.ui_layout import (
    HIGHLIGHT_STYLE,
    MAX_ZEILEN_MENUE,
    MAX_ZEILEN_STANDARD,
    TERMINAL_ZIEL_BREITE,
    baue_standard_tabelle,
    kuerze_text,
    sichtfenster_indizes,
)


class LiveRenderer:
    """
    Zentrale Klasse für Live-Rendering von Menüs und Tabellen.
    Kann für Mehle, Brote oder andere Listen genutzt werden.
    """

    def __init__(self):
        self.console = Console(width=TERMINAL_ZIEL_BREITE)
        self._live: Live = Live(
            console=self.console,
            refresh_per_second=20,
            auto_refresh=False,
            transient=True,
        )
        self._ist_aktiv: bool = False

    def baue_mehle_tabelle(
        self,
        mehle: List[Mehl],
        highlight_index: Optional[int] = None,
        nur_vorhandene: bool = False,
    ) -> Table:
        """
        High-End CI Tabelle für Mehle.
        """

        tabelle = baue_standard_tabelle(
            titel="Brot-Backer | Mehlbestand",
            caption="↑ ↓ Navigieren | ENTER Auswahl | SPACE Bestand | BACK Zurueck",
        )

        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column("Art", style="magenta", max_width=12, overflow="ellipsis")
        tabelle.add_column("Typ", style="green", max_width=12, overflow="ellipsis")
        tabelle.add_column("Eigenname", style="white", max_width=24, overflow="ellipsis")
        tabelle.add_column("Bestand", justify="right", style="bold yellow", width=8)

        if nur_vorhandene:
            mehle = [m for m in mehle if m.vorhandenGramm > 0]

        if not mehle:
            return tabelle

        aktive_zeile = 0 if highlight_index is None else highlight_index
        sichtbare_indizes, hat_oben, hat_unten = sichtfenster_indizes(
            anzahl_zeilen=len(mehle),
            aktiver_index=aktive_zeile,
            max_zeilen=MAX_ZEILEN_STANDARD,
        )

        if hat_oben:
            tabelle.add_row("...", "...", "...", "...", "...", style="dim")

        for index in sichtbare_indizes:
            mehl = mehle[index]
            bestand = mehl.vorhandenGramm

            # Dynamische Bestandsfarbe
            if bestand == 0:
                bestand_text = f"[red]{bestand}[/red]"
            elif bestand < 100:
                bestand_text = f"[yellow]{bestand}[/yellow]"
            else:
                bestand_text = f"[green]{bestand}[/green]"

            # Highlight überschreibt alles
            if highlight_index is not None and index == highlight_index:
                zeilen_style = HIGHLIGHT_STYLE
            else:
                zeilen_style = ""

            tabelle.add_row(
                str(index + 1),
                kuerze_text(mehl.mehlArt, 12),
                kuerze_text(mehl.mehlTyp, 12),
                kuerze_text(mehl.eigenName, 24),
                bestand_text,
                style=zeilen_style,
            )

        if hat_unten:
            tabelle.add_row("...", "...", "...", "...", "...", style="dim")

        return tabelle

    def baue_menu_tabelle(
        self,
        items: List[str],
        highlight_index: Optional[int] = None,
        titel: str = "Menü",
    ) -> Table:
        """
        High-End CI Tabelle für Haupt- und Untermenüs.
        """

        tabelle = baue_standard_tabelle(
            titel=titel,
            caption="↑ ↓ Navigieren | ENTER Auswahl | BACK Zurueck",
        )

        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column(
            "Option",
            style="bold white",
            overflow="ellipsis",
            no_wrap=True,
            max_width=66,
        )

        if not items:
            tabelle.add_row("-", "Keine Optionen")
            return tabelle

        aktive_zeile = 0 if highlight_index is None else highlight_index
        sichtbare_indizes, hat_oben, hat_unten = sichtfenster_indizes(
            anzahl_zeilen=len(items),
            aktiver_index=aktive_zeile,
            max_zeilen=MAX_ZEILEN_MENUE,
        )

        if hat_oben:
            tabelle.add_row("...", "...", style="dim")

        for index in sichtbare_indizes:
            item = items[index]
            # Alternierende Index-Farbe
            if index % 2 == 0:
                index_style = "cyan"
            else:
                index_style = "bright_cyan"

            nummer_text = f"[{index_style}]{index + 1}[/{index_style}]"

            # Highlight für aktive Auswahl
            if highlight_index is not None and index == highlight_index:
                row_style = HIGHLIGHT_STYLE
            else:
                row_style = ""

            tabelle.add_row(
                nummer_text,
                kuerze_text(item, 66),
                style=row_style,
            )

        if hat_unten:
            tabelle.add_row("...", "...", style="dim")

        return tabelle

    def start(self) -> None:
        self.resume()

    def stop(self) -> None:
        self.pause()

    def pause(self) -> None:
        if self._ist_aktiv:
            self._live.stop()
            self._ist_aktiv = False

    def resume(self) -> None:
        if not self._ist_aktiv:
            self._live.start()
            self._ist_aktiv = True

    @contextmanager
    def suspended(self):
        self.pause()
        try:
            yield
        finally:
            self.resume()

    def render_loop(self, render_funktion, navigation: Navigation, input_handler):
        """
        Zentrale Live-Rendering-Schleife.
        - render_funktion() → liefert ein renderbares Rich-Objekt (z.B. Table)
        - navigation → liefert Tasteneingaben
        - input_handler(taste) → verarbeitet Eingabe und gibt optional ein Ergebnis zurück

        Pfeiltasten/OPTIONEN → Loop weiterlaufen
        BACK oder ENTER → Loop beenden, Rückgabe an Aufrufer
        """
        self.resume()

        while True:
            renderbares_objekt = render_funktion()
            self._live.update(renderbares_objekt, refresh=True)

            taste = navigation.lese_taste()
            result = input_handler(taste)

            # Loop nur beenden, wenn BACK oder ENTER erkannt wird
            if result is not None:
                return result
            # sonst weiterlaufen (z.B. Pfeiltasten) ohne None zurückzugeben

    def update(self, renderbares_objekt) -> None:
        """
        Rendert einmalig ein Rich-Objekt im aktuellen Live-Bereich.
        """
        self.resume()
        self._live.update(renderbares_objekt, refresh=True)
