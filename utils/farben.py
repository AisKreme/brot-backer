# Diese Datei enthält zentrale Farbdefinitionen für die Terminal-Ausgabe.
# Es werden ANSI-Escape-Sequenzen verwendet.
# Alle Farben werden an einer Stelle gesammelt, um sauberen und wartbaren Code zu ermöglichen.


# class Farben:
#     """
#     Diese Klasse enthält statische ANSI-Farbwerte für das Terminal.
#     Die Farben können durch einfaches Anhängen an Strings verwendet werden.
#     """

#     # --- Zurücksetzen ---
#     ZURUECKSETZEN: str = "\033[0m"

#     # --- Textfarben ---
#     SCHWARZ: str = "\033[30m"
#     ROT: str = "\033[31m"
#     GRUEN: str = "\033[32m"
#     GELB: str = "\033[33m"
#     BLAU: str = "\033[34m"
#     MAGENTA: str = "\033[35m"
#     CYAN: str = "\033[36m"
#     WEISS: str = "\033[37m"

#     # --- Hintergrundfarben ---
#     HINTERGRUEN_SCHWARZ: str = "\033[40m"
#     HINTERGRUEN_ROT: str = "\033[41m"
#     HINTERGRUEN_GRUEN: str = "\033[42m"
#     HINTERGRUEN_GELB: str = "\033[43m"
#     HINTERGRUEN_BLAU: str = "\033[44m"
#     HINTERGRUEN_MAGENTA: str = "\033[45m"
#     HINTERGRUEN_CYAN: str = "\033[46m"
#     HINTERGRUEN_WEISS: str = "\033[47m"

#     # --- Textstile ---
#     FETT: str = "\033[1m"
#     UNTERSTRICHEN: str = "\033[4m"
