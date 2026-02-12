# Diese Datei kapselt die komplette Tastatur-Navigation im Terminal.
# Sie verwendet readchar, um Pfeiltasten, ENTER und ESC zu erkennen.
# Andere Klassen (z. B. Menu) sollen NICHT direkt mit readchar arbeiten.

import readchar
from readchar import key


class Navigation:
    """
    Diese Klasse ist für das Einlesen und Interpretieren von Tastatureingaben zuständig.
    Sie stellt einfache, verständliche Methoden für die Menü-Navigation bereit.
    """

    def lese_taste(self) -> str:
        """
        Liest genau eine Taste von der Tastatur ein und gibt sie zurück.
        Rückgabewerte sind symbolische Konstanten (z. B. 'UP', 'DOWN', 'ENTER', 'ESC').
        """

        gedrueckteTaste: str = readchar.readkey()

        if gedrueckteTaste == key.UP:
            return "UP"

        if gedrueckteTaste == key.DOWN:
            return "DOWN"

        if gedrueckteTaste == key.LEFT:
            return "LEFT"

        if gedrueckteTaste == key.RIGHT:
            return "RIGHT"

        if gedrueckteTaste == key.ENTER:
            return "ENTER"

        if gedrueckteTaste == "\x20":  # Leertaste
            return "SPACE"

        if gedrueckteTaste == key.BACKSPACE:
            return "BACK"

        # if gedrueckteTaste == "\x1b":
        #     return "ESC"
        if gedrueckteTaste.startswith("\x1b"):
            # ESC nur einmal auswerten
            return "ESC"

        # Alle anderen Tasten werden ignoriert
        return "UNBEKANNT"
