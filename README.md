# Brot-Backer -- Projektübersicht

## Ziel des Projekts

Dieses Python-3-Projekt ist ein terminalbasiertes Lern- und
Praxisprojekt zum Planen, Verwalten und Auswerten von Sauerteigbroten.

Das Projekt verfolgt zwei Hauptziele: - Unterstützung beim Brotbacken
(Rezepte, Hydration, Zeiten, Backvorgänge) - Sauberes Erlernen
objektorientierter Programmierung (OOP) in Python

---

## Gesamtarchitektur

Das Projekt ist in vier Ebenen unterteilt:

1.  Terminal UI (Menüs, Navigation, Farben)
2.  Anwendungslogik (Rezepte, Backvorgänge, Berechnungen)
3.  Datenmodelle (Klassen)
4.  Persistenz (JSON-Dateien)

Die Abhängigkeiten verlaufen immer von oben nach unten.

---

## Zentrale Konzepte

### Mehl

Stammdaten für Mehle, die in mehreren Rezepten verwendet werden können.

Eigenschaften: - Art (z. B. Weizen, Roggen) - Typ (z. B. 405, 1050,
Vollkorn) - Eigenname (optional) - empfohlene Hydration (optional)

### BrotRezept

Beschreibt ein wiederverwendbares Brot-Rezept.

Enthält: - Name - Mehlanteile - Wasser - Salz - Sauerteig - Zusätze -
Zeiten - Berechnung der Hydration

### Backvorgang

Ein konkretes Backereignis eines Rezepts.

Enthält: - Referenz auf ein BrotRezept - Datum - Reale Zeiten -
Temperaturen - Bewertung und Notizen

### Zeiten

Strukturierte Sammlung aller Reife- und Backzeiten: - Autolyse - Dehnen
& Falten - Stockgare (Raum / Kalt) - Stückgare (Raum / Kalt) - Backzeit

### Zusatz

Zusätzliche Zutaten wie Saaten oder Zwiebeln: - Name - Menge - Einheit -
Behandlung (z. B. geröstet)

---

## Klassenübersicht (vereinfacht)

Mehl\
↳ MehlAnteil\
↳ BrotRezept\
↳ Backvorgang

BrotRezept\
↳ Zeiten\
↳ Zusatz

---

## Ordnerstruktur

brot_backer/

- main.py
- daten/
  - mehle.json
  - brote.json
  - backvorgaenge.json
- Klassenpakete/
  - mehl.py
  - mehl_anteil.py
  - zusatz.py
  - zeiten.py
  - brot_rezept.py
  - backvorgang.py
  - json_manager.py
  - menu.py
  - navigation.py
  - ki_assistent.py

---

## Terminal-Bedienung

- Navigation mit Pfeiltasten (readchar)
- ENTER bestätigen, ESC abbrechen
- Schrittweiten:
  - Mehl: 10 g
  - Wasser: 10 ml
  - Sauerteig: 1 g
- Farbige Darstellung zur besseren Übersicht

---

## JSON-Dateien

Die Daten werden in gut lesbaren JSON-Dateien gespeichert:

- mehle.json
- brote.json
- backvorgaenge.json

Die JSON-Dateien enthalten ausschließlich Daten, keine Logik.

---

## KI-Vorbereitung

Geplant ist eine optionale KI-Integration:

- Bewertung von Rezepten
- Vorschläge zur Hydration
- Analyse von Backvorgängen

Die Architektur ist so aufgebaut, dass die KI später ergänzt werden
kann, ohne bestehende Klassen zu ändern.

---

## Entwicklungsphasen

1.  Projektstruktur & Mehlverwaltung
2.  BrotRezept & Hydration
3.  Terminal-Menü & Navigation
4.  Backvorgänge
5.  Feinschliff & KI-Integration

---

## Lernziele

- Objektorientiertes Denken
- Saubere Projektstruktur
- JSON-Datenhaltung
- Terminal-UI mit Tastaturnavigation
- Vorbereitung auf KI-Erweiterungen

---

## Backlog

# 🥖 Brot-Backer Terminal App – Architektur-Refactoring Plan

## 🎯 Ziel

Die Anwendung soll eine professionelle High-End Terminal-App werden, mit:

- Einem zentralen Rendering-System (Rich Live)
- Nur einer Live-Instanz zur selben Zeit
- Einheitlicher Navigation
- Keine doppelten Event-Loops
- Keine mehrfach implementierte Pfeiltasten-Logik
- Klare Trennung von UI, Logik und Daten

---

# 🔍 Aktuelle Probleme

## ❌ 1. Mehrere Live-Instanzen

Aktuell werden mehrere `Live()` Kontexte erzeugt:

- In `Menu`
- In `mehl_per_pfeiltasten_auswaehlen`
- Teilweise bei Tabellenanzeige

Das führt zu:

- Flackern
- Doppeltem Rendering
- Inkonsistenter Darstellung

---

## ❌ 2. Navigation wird mehrfach instanziiert

Es existieren mehrere `Navigation()` Objekte.

Ziel:
👉 Pro UI-Kontext genau **eine Navigation-Instanz**.

---

## ❌ 3. Doppelte Pfeiltasten-Logik

Die gleiche Logik existiert in:

- `Menu`
- `mehl_per_pfeiltasten_auswaehlen`
- `neues_mehl_hinzufuegen`

Ziel:
👉 Eine zentrale Auswahl-Logik.

---

## ❌ 4. LiveRenderer wird nicht zentral genutzt

Er baut Tabellen, kontrolliert aber nicht das Rendering.

Ziel:
👉 LiveRenderer wird das zentrale UI-System.

---

# 🏗 Zielarchitektur

```
App
 └── LiveRenderer (eine Instanz)
      ├── render(Menu)
      ├── render(Mehle Tabelle)
      ├── render(Bearbeiten View)
      └── render(Info View)
```

Nicht mehr:

```
Menu → eigenes Live
MehleMenu → eigenes Live
Tabellen → eigenes Live
```

---

# 🚀 Refactoring-Schritte

## ✅ Schritt 1 – LiveRenderer zentralisieren

- Eine Console
- Eine Live-Instanz
- Eine zentrale render_loop()

---

## ✅ Schritt 2 – MehleMenu bereinigen

Entfernen:

- `from rich.live import Live`
- `Console()` Instanzen
- Eigene Live-Kontexte
- Eigene Navigation-Instanzen

---

## ✅ Schritt 3 – start()-Methode umbauen

Keine eigene Event-Loop mehr.
Nur:

```
auswahlIndex = self.menu.anzeigen(self.navigation)
```

---

## ✅ Schritt 4 – Auswahl-Logik vereinheitlichen

`mehl_per_pfeiltasten_auswaehlen` soll keine eigene Live-Logik mehr enthalten.

---

## ✅ Schritt 5 – Neues Mehl hinzufügen vereinheitlichen

Keine eigenen while-Loops mehr.
Nur noch Nutzung von `Menu.anzeigen()`.

---

# 🧠 Endziel

- Kein Flackern
- Kein doppeltes Rendering
- Eine Live-Instanz
- Saubere Architektur
- Professionelle Terminal-App-Struktur

---

# 📌 Nächster Schritt

Wir gehen das Refactoring nun Schritt für Schritt durch:

1. LiveRenderer finalisieren
2. Menu vollständig auf LiveRenderer umbauen
3. MehleMenu bereinigen
4. Navigation vereinheitlichen
5. JSON-Zugriff sauber kapseln

---

💡 Ziel: Eine stabile, erweiterbare Terminal-App-Architektur mit sauberer UI-Trennung.
