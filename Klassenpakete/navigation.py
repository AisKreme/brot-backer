# Diese Datei kapselt die komplette Tastatur-Navigation im Terminal.
# Sie verwendet readchar, um Pfeiltasten, ENTER und ESC zu erkennen.
# Andere Klassen (z. B. Menu) sollen NICHT direkt mit readchar arbeiten.

import select
import sys
import termios
import tty
import os

import readchar
from readchar import key


class Navigation:
    """
    Diese Klasse ist für das Einlesen und Interpretieren von Tastatureingaben zuständig.
    Sie stellt einfache, verständliche Methoden für die Menü-Navigation bereit.
    """

    def _interpretiere_taste(self, gedrueckteTaste: str) -> str:
        if gedrueckteTaste == key.UP or gedrueckteTaste == "\x1b[A":
            return "UP"

        if gedrueckteTaste == key.DOWN or gedrueckteTaste == "\x1b[B":
            return "DOWN"

        if gedrueckteTaste == key.LEFT or gedrueckteTaste == "\x1b[D":
            return "LEFT"

        if gedrueckteTaste == key.RIGHT or gedrueckteTaste == "\x1b[C":
            return "RIGHT"

        if gedrueckteTaste in (key.ENTER, "\r", "\n"):
            return "ENTER"

        if gedrueckteTaste == "\x20":  # Leertaste
            return "SPACE"

        if gedrueckteTaste in (key.BACKSPACE, "\x7f", "\x08"):
            return "BACK"

        if gedrueckteTaste == "\x1b" or gedrueckteTaste.startswith("\x1b"):
            return "ESC"

        if len(gedrueckteTaste) == 1 and gedrueckteTaste.isalpha():
            return gedrueckteTaste.lower()

        return "UNBEKANNT"

    def lese_taste(self) -> str:
        """
        Liest genau eine Taste von der Tastatur ein und gibt sie zurück.
        Rückgabewerte sind symbolische Konstanten (z. B. 'UP', 'DOWN', 'ENTER', 'ESC').
        """

        gedrueckteTaste: str = readchar.readkey()
        return self._interpretiere_taste(gedrueckteTaste)

    def lese_taste_mit_timeout(self, timeout_sekunden: float) -> str | None:
        """
        Liest eine Taste mit Timeout.
        - Taste gefunden: normaler Rueckgabewert wie in lese_taste()
        - Keine Taste innerhalb Timeout: None
        """
        timeout = max(0.0, float(timeout_sekunden))
        fd = sys.stdin.fileno()
        alte_einstellungen = termios.tcgetattr(fd)
        try:
            # CBreak: Zeichen kommen sofort (kein ENTER noetig), aber ohne Voll-Raw
            tty.setcbreak(fd)
            ready, _, _ = select.select([fd], [], [], timeout)
            if not ready:
                return None

            taste = os.read(fd, 1).decode(errors="ignore")
            if not taste:
                return None

            if taste == "\x1b":
                # Restliche Bytes (z. B. Pfeiltasten-Sequenzen) einsammeln
                sequenz = [taste]
                while True:
                    more, _, _ = select.select([fd], [], [], 0)
                    if not more:
                        break
                    teil = os.read(fd, 1).decode(errors="ignore")
                    if not teil:
                        break
                    sequenz.append(teil)
                taste = "".join(sequenz)

            return self._interpretiere_taste(taste)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, alte_einstellungen)
