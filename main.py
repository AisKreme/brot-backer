# Einstiegspunkt des Brot-Backer-Programms.
# Diese Datei verbindet Menü, Navigation und Programmfluss.
# Hier befindet sich bewusst KEINE Fachlogik (Rezepte, Mehle, etc.).

from Klassenpakete.liveRenderer import LiveRenderer
from Klassenpakete.backvorgang_menu import BackvorgangMenu
from Klassenpakete.daten_menu import DatenMenu
from Klassenpakete.ki_assistent import KiAssistentMenu
from Klassenpakete.mehle_menu import MehleMenu
from Klassenpakete.rezepte_menu import RezepteMenu
from Klassenpakete.menu import Menu
from Klassenpakete.navigation import Navigation


def main() -> None:
    """
    Hauptfunktion des Programms.
    Sie initialisiert das Menü und startet die Ereignisschleife.
    """

    # Definition der Menüeinträge
    menuePunkte: list[str] = [
        "Backvorgang starten",
        "Rezepte verwalten",
        "Mehle verwalten",
        "Daten anzeigen",
        "KI fragen",
        "Beenden",
    ]

    # Menü- und Navigationsobjekte erstellen
    menu: Menu = Menu(menuePunkte=menuePunkte)
    navigation: Navigation = Navigation()
    renderer = LiveRenderer()

    programmLaeuft: bool = True
    renderer.start()
    try:
        # Haupt-Ereignisschleife
        while programmLaeuft:
            # Hauptmenü anzeigen und Auswahl holen
            auswahl = menu.anzeigen(navigation, renderer)

            if auswahl in ("BACK", "ESC"):
                programmLaeuft = False
                break

            if isinstance(auswahl, int):
                ausgewaehlterPunkt = menuePunkte[auswahl]

                if ausgewaehlterPunkt == "Backvorgang starten":
                    menu.starte_untermenue(BackvorgangMenu(), navigation, renderer)
                elif ausgewaehlterPunkt == "Rezepte verwalten":
                    menu.starte_untermenue(RezepteMenu(), navigation, renderer)
                elif ausgewaehlterPunkt == "Daten anzeigen":
                    menu.starte_untermenue(DatenMenu(), navigation, renderer)
                elif ausgewaehlterPunkt == "Mehle verwalten":
                    menu.starte_untermenue(MehleMenu(), navigation, renderer)
                elif ausgewaehlterPunkt == "KI fragen":
                    menu.starte_untermenue(KiAssistentMenu(), navigation, renderer)
                elif ausgewaehlterPunkt == "Beenden":
                    programmLaeuft = False
    finally:
        renderer.stop()


if __name__ == "__main__":
    main()
