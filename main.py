# Einstiegspunkt des Brot-Backer-Programms.
# Diese Datei verbindet Menü, Navigation und Programmfluss.
# Hier befindet sich bewusst KEINE Fachlogik (Rezepte, Mehle, etc.).

from Klassenpakete.liveRenderer import LiveRenderer
from Klassenpakete.mehle_menu import MehleMenu
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

                if ausgewaehlterPunkt == "Mehle verwalten":
                    menu.starte_untermenue(MehleMenu(), navigation, renderer)
                elif ausgewaehlterPunkt == "Beenden":
                    programmLaeuft = False
    finally:
        renderer.stop()


if __name__ == "__main__":
    main()
