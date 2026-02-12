# Diese Datei enthält die Menü-Klasse für das Terminal-Menü.
# Sie ist ausschließlich für Darstellung und Auswahl zuständig.
# Es wird hier bewusst keine Fachlogik (Rezepte, Mehle, etc.) verwendet.

from typing import List


class Menu:
    """
    Diese Klasse stellt ein einfaches Terminal-Menü dar.
    Der Benutzer kann mit den Pfeiltasten navigieren.
    """

    def __init__(self, menuePunkte: List[str]) -> None:
        # Liste aller Menüeinträge (reine Texte)
        self.menuePunkte: List[str] = menuePunkte

        # Index des aktuell ausgewählten Menüpunktes
        self.aktuellerIndex: int = 0

    def anzeigen(self, navigation, renderer) -> int | None:
        """
        Zeigt das Menü über das zentrale LiveRenderer-System an.
        Rückgabe:
            - Index des ausgewählten Menüpunktes bei ENTER
            - None bei BACK
        """

        def render():
            return renderer.baue_menu_tabelle(
                items=self.menuePunkte,
                highlight_index=self.aktuellerIndex,
                titel="🍞  Brot-Backer 🍞",
            )

        def input_handler(taste: str):
            if taste == "UP":
                self.nach_oben()
            elif taste == "DOWN":
                self.nach_unten()
            elif taste == "ENTER":
                return self.auswahl_holen()
            elif taste == "BACK":
                return taste
            return None

        return renderer.render_loop(render, navigation, input_handler)

    def nach_oben(self) -> None:
        """
        Bewegt die Auswahl im Menü eine Position nach oben.
        Wenn bereits oben, springt zum letzten Eintrag.
        """
        if self.aktuellerIndex > 0:
            self.aktuellerIndex -= 1
        else:
            self.aktuellerIndex = len(self.menuePunkte) - 1

    def nach_unten(self) -> None:
        """
        Bewegt die Auswahl im Menü eine Position nach unten.
        Wenn bereits unten, springt zum ersten Eintrag.
        """
        if self.aktuellerIndex < len(self.menuePunkte) - 1:
            self.aktuellerIndex += 1
        else:
            self.aktuellerIndex = 0

    def auswahl_holen(self) -> int:
        """
        Gibt den Index des aktuell ausgewählten Menüpunktes zurück.
        """
        return self.aktuellerIndex

    def starte_untermenue(self, untermenue, navigation, renderer) -> None:
        """
        Zeigt ein Untermenü (z.B. MehleMenu) live über das zentrale LiveRenderer-System an.
        """
        untermenue.starten(navigation, renderer)
