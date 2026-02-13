from __future__ import annotations

from rich import box
from rich.table import Table


TERMINAL_ZIEL_BREITE = 80
TERMINAL_ZIEL_HOEHE = 25
MAX_ZEILEN_STANDARD = 10
MAX_ZEILEN_KOMPAKT = 6
MAX_ZEILEN_MENUE = 10
HIGHLIGHT_STYLE = "bold black on bright_yellow"
HEADER_STYLE = "bold white on dark_green"
BORDER_STYLE = "grey35"
TITEL_STYLE = "bold bright_white"


def baue_standard_tabelle(
    titel: str,
    caption: str | None = None,
    expand: bool = True,
) -> Table:
    return Table(
        title=f"[{TITEL_STYLE}]{titel}[/{TITEL_STYLE}]",
        expand=expand,
        box=box.ROUNDED,
        header_style=HEADER_STYLE,
        border_style=BORDER_STYLE,
        caption=f"[dim]{caption}[/dim]" if caption else None,
        pad_edge=False,
    )


def kuerze_text(text: str | None, max_len: int) -> str:
    if not text:
        return "-"
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def sichtfenster_indizes(
    anzahl_zeilen: int,
    aktiver_index: int = 0,
    max_zeilen: int = MAX_ZEILEN_STANDARD,
) -> tuple[list[int], bool, bool]:
    """
    Liefert ein kompaktes Fenster ueber eine groessere Liste:
    - sichtbare Indizes
    - hat_zeilen_davor
    - hat_zeilen_danach
    """
    if anzahl_zeilen <= 0:
        return [], False, False

    max_zeilen = max(1, max_zeilen)

    if anzahl_zeilen <= max_zeilen:
        return list(range(anzahl_zeilen)), False, False

    aktiver_index = max(0, min(aktiver_index, anzahl_zeilen - 1))
    halb = max_zeilen // 2
    start = max(0, aktiver_index - halb)
    ende = start + max_zeilen

    if ende > anzahl_zeilen:
        ende = anzahl_zeilen
        start = ende - max_zeilen

    return list(range(start, ende)), start > 0, ende < anzahl_zeilen
