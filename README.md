# brot-backer

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Aktiv-brightgreen)](https://github.com/AisKreme/brot-backer)
[![Letzter Commit](https://img.shields.io/github/last-commit/AisKreme/brot-backer)](https://github.com/AisKreme/brot-backer/commits)
[![Lizenz](https://img.shields.io/github/license/AisKreme/brot-backer)](#lizenz)
[![Stars](https://img.shields.io/github/stars/AisKreme/brot-backer?style=social)](https://github.com/AisKreme/brot-backer/stargazers)

Terminalbasierte Python-App zum Planen, Durchführen und Auswerten von Brot-Backvorgängen – inklusive Rezeptverwaltung, Mehlbestand und KI-Analyse.

## Quickstart (60 Sekunden)

```bash
git clone https://github.com/AisKreme/brot-backer.git
cd brot-backer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Was das Programm macht

- Verwalten von **Mehlen** (Art, Typ, Bestand in Gramm)
- Anzeigen und Bearbeiten von **Rezepten** (Hydration, Formel, Prozess, Backprofil)
- Starten, Pausieren, Fortsetzen und Abschließen von **Backvorgängen**
- Geführtes **Schritt-Tracking mit Timer**
- Bearbeiten von `ingredient_usage` pro Backvorgang (Soll/Ist/Abzug)
- Automatischer **Bestandsabzug** nach Abschluss
- **KI-Assistent** für Bewertung, Verbesserungsvorschläge und Verlaufsansicht

## Voraussetzungen

- Python **3.10+** (empfohlen: 3.11 oder 3.12)
- Terminal mit Tastatureingaben (z. B. iTerm2)

## Installation (ausführlich)

Wichtig: Es müssen **alle Pakete aus `requirements.txt`** installiert werden.

1. Repository klonen:

```bash
git clone https://github.com/AisKreme/brot-backer.git
cd brot-backer
```

2. Virtuelle Umgebung erstellen und aktivieren:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

## Anforderungen aus `requirements.txt`

- `readchar`
- `rich`
- `google-genai`

Auch wenn KI optional ist, sollte `google-genai` installiert sein, damit das Menü vollständig funktioniert.

## Anwendung starten

```bash
python3 main.py
```

Hinweise:

- `GOOGLE_API_KEY` ist für KI-Anfragen erforderlich.
- `GOOGLE_MODEL` ist optional; ohne Angabe wird ein Standardmodell verwendet.
- `.env` ist in `.gitignore` eingetragen und sollte nicht committed werden.

## Bedienung im Terminal

Globale Steuerung:

- `UP` / `DOWN`: Navigation in Menüs und Listen
- `LEFT` / `RIGHT`: Seitenwechsel in Detailansichten
- `ENTER`: Auswahl bestätigen
- `BACKSPACE`: Zurück
- `ESC`: Abbrechen/Zurück

Backvorgang-Tracking:

- `ENTER`: Schritt starten bzw. Timer-Schritt beenden
- `p`: Backvorgang pausieren

## Menü-Übersicht

1. **Backvorgang starten**

- Neuen Backvorgang aus Rezept anlegen
- Skalierungsfaktor setzen (`scale_factor`)
- Zutaten je Backvorgang anpassen
- Geführtes Tracking mit Timer
- Laufende/pausierte Backvorgänge fortsetzen

2. **Rezepte verwalten**

- Rezepte anzeigen
- Rezeptdaten bearbeiten
- Prozessschritte und Backprofil pflegen

3. **Mehle verwalten**

- Mehlbestand anzeigen
- Neues Mehl hinzufügen
- Mehle bearbeiten/löschen

4. **Daten anzeigen**

- Laufende und pausierte Backvorgänge als Übersicht

5. **KI fragen**

- Backvorgang analysieren lassen
- KI-Vorschläge als Diff prüfen und übernehmen
- KI-Bewertungen speichern
- Gespeicherte KI-Antworten strukturiert anzeigen

## Datenablage (JSON)

Alle Programmdaten liegen unter `daten/`:

- `mehle.json` – Mehlstammdaten und Bestand
- `brote.json` – Rezepte
- `backvorgaenge.json` – Backvorgänge und Trackingdaten
- `ki_anfragen.json` – gespeicherte KI-Antworten

Schema-Grundstruktur:

```json
{
  "schema_version": 1,
  "updated_at": "ISO-8601",
  "items": []
}
```

## Projektstruktur

```text
brot-backer/
├── main.py
├── requirements.txt
├── .env
├── daten/
│   ├── mehle.json
│   ├── brote.json
│   ├── backvorgaenge.json
│   └── ki_anfragen.json
└── Klassenpakete/
    ├── backvorgang.py
    ├── backvorgang_menu.py
    ├── brot_rezept.py
    ├── daten_menu.py
    ├── json_manager.py
    ├── ki_assistent.py
    ├── liveRenderer.py
    ├── mehl.py
    ├── mehle_menu.py
    ├── menu.py
    ├── navigation.py
    ├── rezepte_menu.py
    ├── ui_layout.py
    ├── zeiten.py
    └── zusatz.py
```

## Häufige Probleme

- `GOOGLE_API_KEY ist nicht gesetzt`
  - `.env` prüfen oder API-Key im KI-Menü hinterlegen.
- `ModuleNotFoundError`
  - Virtuelle Umgebung aktivieren und `pip install -r requirements.txt` ausführen.
- Leere Tabellen/Ansichten
  - Prüfen, ob in `daten/*.json` bereits Einträge vorhanden sind.
