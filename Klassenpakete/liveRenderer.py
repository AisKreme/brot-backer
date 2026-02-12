from contextlib import contextmanager
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

from Klassenpakete.mehl import Mehl
from Klassenpakete.navigation import Navigation


class LiveRenderer:
    """
    Zentrale Klasse für Live-Rendering von Menüs und Tabellen.
    Kann für Mehle, Brote oder andere Listen genutzt werden.
    """

    def __init__(self):
        self.console = Console()
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

        tabelle = Table(
            title="[bold bright_white]🍞  Brot-Backer | Mehlbestand[/bold bright_white]",
            expand=True,
            box=box.ROUNDED,
            header_style="bold white on dark_green",
            # row_styles=["none", "grey19"],
            border_style="grey35",
            caption="[dim]↑ ↓ Navigieren  |  ENTER Auswahl  |  SPACE Bestand  |  BACK Zurück[/dim]",
        )

        tabelle.add_column("Nr.", style="bold cyan", justify="right")
        tabelle.add_column("Art", style="magenta")
        tabelle.add_column("Typ", style="green")
        tabelle.add_column("Eigenname", style="white")
        tabelle.add_column("Bestand (g)", justify="right", style="bold yellow")

        if nur_vorhandene:
            mehle = [m for m in mehle if m.vorhandenGramm > 0]

        if not mehle:
            return tabelle

        for index, mehl in enumerate(mehle):
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
                zeilen_style = "bold black on bright_yellow"
            else:
                zeilen_style = ""

            tabelle.add_row(
                str(index + 1),
                mehl.mehlArt,
                mehl.mehlTyp,
                mehl.eigenName or "-",
                bestand_text,
                style=zeilen_style,
            )

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

        tabelle = Table(
            title=f"[bold bright_white]{titel}[/bold bright_white]",
            expand=True,
            box=box.ROUNDED,
            header_style="bold white on dark_green",
            border_style="grey35",
            caption="[dim]↑ ↓ Navigieren  |  ENTER Auswahl  |  BACK Zurück[/dim]",
        )

        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column("Option", style="bold white")

        for index, item in enumerate(items):
            # Alternierende Index-Farbe
            if index % 2 == 0:
                index_style = "cyan"
            else:
                index_style = "bright_cyan"

            nummer_text = f"[{index_style}]{index + 1}[/{index_style}]"

            # Highlight für aktive Auswahl
            if highlight_index is not None and index == highlight_index:
                row_style = "bold black on bright_yellow"
            else:
                row_style = ""

            tabelle.add_row(
                nummer_text,
                item,
                style=row_style,
            )

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
