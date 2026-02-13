from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from google import genai
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from Klassenpakete.backvorgang import Backvorgang, ZutatenVerbrauch
from Klassenpakete.brot_rezept import BrotRezept
from Klassenpakete.json_manager import JsonManager
from Klassenpakete.menu import Menu
from Klassenpakete.ui_layout import (
    HIGHLIGHT_STYLE,
    MAX_ZEILEN_KOMPAKT,
    MAX_ZEILEN_STANDARD,
    baue_standard_tabelle,
    kuerze_text,
    sichtfenster_indizes,
)


@dataclass
class KiVerlaufEintrag:
    id: str
    created_at: str
    backvorgang_id: str
    recipe_id: str
    recipe_name: str
    model: str
    status_snapshot: str
    user_question: str = ""
    overall_rating_1_10: int = 0
    summary: str = ""
    review: dict[str, Any] = field(default_factory=dict)
    ingredient_changes_applied: int = 0
    review_in_backvorgang_saved: bool = False
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, daten: dict[str, Any]) -> "KiVerlaufEintrag":
        known_keys = {
            "id",
            "created_at",
            "backvorgang_id",
            "recipe_id",
            "recipe_name",
            "model",
            "status_snapshot",
            "user_question",
            "overall_rating_1_10",
            "summary",
            "review",
            "ingredient_changes_applied",
            "review_in_backvorgang_saved",
        }
        extra_fields = {k: v for k, v in daten.items() if k not in known_keys}

        try:
            rating = int(daten.get("overall_rating_1_10", 0))
        except (TypeError, ValueError):
            rating = 0

        try:
            applied = int(daten.get("ingredient_changes_applied", 0))
        except (TypeError, ValueError):
            applied = 0

        review = daten.get("review", {})
        if not isinstance(review, dict):
            review = {}

        return cls(
            id=str(daten.get("id", "")).strip(),
            created_at=str(daten.get("created_at", "")).strip(),
            backvorgang_id=str(daten.get("backvorgang_id", "")).strip(),
            recipe_id=str(daten.get("recipe_id", "")).strip(),
            recipe_name=str(daten.get("recipe_name", "")).strip(),
            model=str(daten.get("model", "")).strip(),
            status_snapshot=str(daten.get("status_snapshot", "")).strip(),
            user_question=str(daten.get("user_question", "")).strip(),
            overall_rating_1_10=max(0, min(10, rating)),
            summary=str(daten.get("summary", "")).strip(),
            review=review,
            ingredient_changes_applied=max(0, applied),
            review_in_backvorgang_saved=bool(daten.get("review_in_backvorgang_saved", False)),
            extra_fields=extra_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "created_at": self.created_at,
            "backvorgang_id": self.backvorgang_id,
            "recipe_id": self.recipe_id,
            "recipe_name": self.recipe_name,
            "model": self.model,
            "status_snapshot": self.status_snapshot,
            "user_question": self.user_question,
            "overall_rating_1_10": self.overall_rating_1_10,
            "summary": self.summary,
            "review": self.review,
            "ingredient_changes_applied": self.ingredient_changes_applied,
            "review_in_backvorgang_saved": self.review_in_backvorgang_saved,
        }
        for key, value in self.extra_fields.items():
            if key not in result:
                result[key] = value
        return result


class KiAssistentMenu:
    """
    KI-Untermenue fuer Meisterbaecker-Bewertungen.
    """

    def __init__(self) -> None:
        self.menuePunkte: list[str] = [
            "Backvorgang mit KI bewerten",
            "Gespeicherte KI-Antworten anzeigen",
            "Verfuegbare KI-Modelle anzeigen",
            "API-Key in .env hinterlegen",
            "Zurueck",
        ]
        self.menu: Menu = Menu(menuePunkte=self.menuePunkte)
        self.backvorgangManager: JsonManager = JsonManager("daten/backvorgaenge.json")
        self.rezeptManager: JsonManager = JsonManager("daten/brote.json")
        self.kiVerlaufManager: JsonManager = JsonManager("daten/ki_anfragen.json")
        self.env_datei: Path = Path(__file__).parent.parent / ".env"
        self.model_name: str = (
            os.getenv("GOOGLE_MODEL")
            or self._lade_wert_aus_env_datei("GOOGLE_MODEL")
            or "gemini-2.5-flash-lite"
        )
        self._client: genai.Client | None = None

    def starten(self, navigation, renderer) -> None:
        self.renderer = renderer
        self.navigation = navigation

        while True:
            auswahlIndex = self.menu.anzeigen(navigation, renderer)

            if auswahlIndex == "BACK":
                return

            if not isinstance(auswahlIndex, int):
                return

            ausgewaehlterPunkt = self.menuePunkte[auswahlIndex]

            if ausgewaehlterPunkt == "Backvorgang mit KI bewerten":
                self._backvorgang_ki_bewerten(navigation)
            elif ausgewaehlterPunkt == "Gespeicherte KI-Antworten anzeigen":
                self._ki_verlauf_anzeigen(navigation)
            elif ausgewaehlterPunkt == "Verfuegbare KI-Modelle anzeigen":
                self._modelle_anzeigen()
            elif ausgewaehlterPunkt == "API-Key in .env hinterlegen":
                self._api_key_verwalten()
            elif ausgewaehlterPunkt == "Zurueck":
                return

    def _hole_client(self) -> genai.Client | None:
        if self._client is not None:
            return self._client

        key = self._hole_api_key()
        if not key:
            with self.renderer.suspended():
                print("\nGOOGLE_API_KEY ist nicht gesetzt.")
                print(
                    "Nutze im Menue den Punkt 'API-Key in .env hinterlegen' "
                    "oder setze die Variable manuell."
                )
                input("ENTER druecken, um zurueckzukehren...")
            return None

        try:
            self._client = genai.Client(api_key=key)
            return self._client
        except Exception as exc:  # pragma: no cover - defensive
            with self.renderer.suspended():
                print(f"\nKI-Client konnte nicht erstellt werden: {exc}")
                input("ENTER druecken, um zurueckzukehren...")
            return None

    def _hole_api_key(self) -> str | None:
        key = os.getenv("GOOGLE_API_KEY")
        if key:
            return key.strip() or None

        key_aus_datei = self._lade_wert_aus_env_datei("GOOGLE_API_KEY")
        if key_aus_datei:
            # Fuer die laufende Session verfuegbar machen.
            os.environ["GOOGLE_API_KEY"] = key_aus_datei
            return key_aus_datei
        return None

    def _api_key_verwalten(self) -> None:
        aktueller_key = self._hole_api_key()
        quelle = (
            "Environment-Variable"
            if os.getenv("GOOGLE_API_KEY")
            else (".env-Datei" if aktueller_key else "nicht gesetzt")
        )
        maskiert = self._maskiere_api_key(aktueller_key)

        with self.renderer.suspended():
            print("\nAPI-Key Verwaltung")
            print(f"Aktueller Status: {quelle}")
            print(f"Aktueller Key: {maskiert}")
            print("\nNeuen Key eingeben und ENTER zum Speichern.")
            print("Leer lassen = Abbrechen | '-' = aus .env entfernen")
            neu = input("GOOGLE_API_KEY: ").strip()

        if not neu:
            return

        if neu == "-":
            self._schreibe_env_wert("GOOGLE_API_KEY", None)
            if "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]
            self._client = None
            with self.renderer.suspended():
                print("\nGOOGLE_API_KEY wurde aus .env entfernt.")
                input("ENTER druecken, um zurueckzukehren...")
            return

        self._schreibe_env_wert("GOOGLE_API_KEY", neu)
        os.environ["GOOGLE_API_KEY"] = neu
        self._client = None
        with self.renderer.suspended():
            print("\nGOOGLE_API_KEY wurde in .env gespeichert.")
            input("ENTER druecken, um zurueckzukehren...")

    def _lade_wert_aus_env_datei(self, key: str) -> str | None:
        if not self.env_datei.exists():
            return None

        try:
            zeilen = self.env_datei.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        praefix = f"{key}="
        for zeile in zeilen:
            text = zeile.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            if not text.startswith(praefix):
                continue

            roh = text[len(praefix) :].strip()
            if not roh:
                return None
            if (roh.startswith('"') and roh.endswith('"')) or (
                roh.startswith("'") and roh.endswith("'")
            ):
                roh = roh[1:-1]
                roh = roh.replace('\\"', '"').replace("\\\\", "\\")
            return roh.strip() or None
        return None

    def _schreibe_env_wert(self, key: str, value: str | None) -> None:
        bestehend: list[str] = []
        if self.env_datei.exists():
            try:
                bestehend = self.env_datei.read_text(encoding="utf-8").splitlines()
            except OSError:
                bestehend = []

        praefix = f"{key}="
        neue_zeilen: list[str] = []
        ersetzt = False
        for zeile in bestehend:
            stripped = zeile.strip()
            if stripped.startswith(praefix):
                ersetzt = True
                if value is not None:
                    neue_zeilen.append(f'{key}="{self._escape_env_value(value)}"')
                continue
            neue_zeilen.append(zeile)

        if not ersetzt and value is not None:
            neue_zeilen.append(f'{key}="{self._escape_env_value(value)}"')

        inhalt = "\n".join(neue_zeilen).rstrip() + "\n"
        self.env_datei.write_text(inhalt, encoding="utf-8")

    def _escape_env_value(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _maskiere_api_key(self, key: str | None) -> str:
        if not key:
            return "-"
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + ("*" * (len(key) - 8)) + key[-4:]

    def _backvorgang_ki_bewerten(self, navigation) -> None:
        backvorgaenge = self.backvorgangManager.laden(Backvorgang)
        if not backvorgaenge:
            with self.renderer.suspended():
                print("\nKeine Backvorgaenge vorhanden.")
                input("ENTER druecken, um zurueckzukehren...")
            return

        auswahl = self._backvorgang_auswaehlen(backvorgaenge, navigation)
        if not isinstance(auswahl, int):
            return

        backvorgang = backvorgaenge[auswahl]
        rezept = self._hole_rezept(backvorgang.recipe_id)

        with self.renderer.suspended():
            zusatzfrage = input(
                "Optionale Zusatzfrage an die KI (optional): "
            ).strip()

        review = self._frage_meisterbaecker_ki(backvorgang, rezept, zusatzfrage)
        if review is None:
            return

        self._zeige_review_kompakt(review)

        with self.renderer.suspended():
            roh_anzeigen = input("Roh-JSON anzeigen? (j/n) [n]: ").strip().lower()
            if roh_anzeigen in ("j", "ja", "y", "yes"):
                print("\nKI-Antwort (JSON):\n")
                print(json.dumps(review, ensure_ascii=False, indent=2))

            vorschlaege_anwenden = (
                input("ingredient_usage-Vorschlaege anwenden? (j/n) [n]: ")
                .strip()
                .lower()
            )
            speichern = input(
                "\nKI-Bewertung im Backvorgang speichern? (j/n) [j]: "
            ).strip().lower()

        hat_geaendert = False
        uebernommene_ingredient_aenderungen = 0
        if vorschlaege_anwenden in ("j", "ja", "y", "yes"):
            aenderungen = self._ermittle_ingredient_suggestion_aenderungen(
                backvorgang,
                review,
            )
            if not aenderungen:
                with self.renderer.suspended():
                    print("\nKeine verwertbaren ingredient_usage-Vorschlaege gefunden.")
                    input("ENTER druecken, um fortzufahren...")
            else:
                self._zeige_ingredient_diff_vorschau(aenderungen)
                with self.renderer.suspended():
                    uebernehmen = (
                        input("Diese Aenderungen uebernehmen? (j/n) [j]: ")
                        .strip()
                        .lower()
                    )
                if uebernehmen in ("", "j", "ja", "y", "yes"):
                    anzahl = self._wende_ingredient_aenderungen_an(
                        backvorgang,
                        aenderungen,
                    )
                    uebernommene_ingredient_aenderungen = anzahl
                    hat_geaendert = anzahl > 0
                    with self.renderer.suspended():
                        print(f"\n{anzahl} ingredient_usage-Aenderungen uebernommen.")
                        input("ENTER druecken, um fortzufahren...")
                else:
                    with self.renderer.suspended():
                        print("\nUebernahme abgebrochen.")
                        input("ENTER druecken, um fortzufahren...")

        review_gespeichert = False
        if speichern in ("", "j", "ja", "y", "yes"):
            self._speichere_ki_review(backvorgaenge, auswahl, review)
            review_gespeichert = True

        self._speichere_ki_verlauf(
            backvorgang=backvorgang,
            review=review,
            user_question=zusatzfrage,
            ingredient_changes_applied=uebernommene_ingredient_aenderungen,
            review_in_backvorgang_saved=review_gespeichert,
        )

        if hat_geaendert or review_gespeichert:
            backvorgang.updated_at = datetime.now().astimezone().isoformat(timespec="seconds")
            self.backvorgangManager.speichern(backvorgaenge)
            if review_gespeichert:
                with self.renderer.suspended():
                    print("KI-Bewertung wurde gespeichert.")
                    input("ENTER druecken, um fortzufahren...")

    def _speichere_ki_verlauf(
        self,
        backvorgang: Backvorgang,
        review: dict[str, Any],
        user_question: str,
        ingredient_changes_applied: int,
        review_in_backvorgang_saved: bool,
    ) -> None:
        eintraege = self.kiVerlaufManager.laden(KiVerlaufEintrag)
        rating = review.get("overall_rating_1_10")
        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            rating_int = 0
        rating_int = max(0, min(10, rating_int))

        eintraege.append(
            KiVerlaufEintrag(
                id=f"ki_{uuid4().hex[:12]}",
                created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                backvorgang_id=backvorgang.id,
                recipe_id=backvorgang.recipe_id,
                recipe_name=backvorgang.recipe_snapshot.name or backvorgang.recipe_id,
                model=self.model_name,
                status_snapshot=backvorgang.status,
                user_question=user_question,
                overall_rating_1_10=rating_int,
                summary=str(review.get("summary", "")).strip(),
                review=review,
                ingredient_changes_applied=max(0, int(ingredient_changes_applied)),
                review_in_backvorgang_saved=review_in_backvorgang_saved,
            )
        )
        self.kiVerlaufManager.speichern(eintraege)

    def _ki_verlauf_anzeigen(self, navigation) -> None:
        highlight_index = 0

        while True:
            verlauf = self.kiVerlaufManager.laden(KiVerlaufEintrag)
            if not verlauf:
                with self.renderer.suspended():
                    print("\nNoch keine KI-Anfragen gespeichert.")
                    input("ENTER druecken, um zurueckzukehren...")
                return

            verlauf_sortiert = sorted(
                verlauf,
                key=lambda x: x.created_at or "",
                reverse=True,
            )
            highlight_index = min(highlight_index, len(verlauf_sortiert) - 1)

            def render():
                return self._baue_ki_verlauf_browser(
                    verlauf=verlauf_sortiert,
                    highlight_index=highlight_index,
                )

            def input_handler(taste: str):
                nonlocal highlight_index
                if taste == "UP":
                    highlight_index = (highlight_index - 1) % len(verlauf_sortiert)
                elif taste == "DOWN":
                    highlight_index = (highlight_index + 1) % len(verlauf_sortiert)
                elif taste == "ENTER":
                    return "OPEN_DETAIL"
                elif taste in ("BACK", "ESC"):
                    return "BACK"
                return None

            result = self.renderer.render_loop(render, navigation, input_handler)
            if result == "OPEN_DETAIL":
                self._zeige_ki_verlauf_detail(verlauf_sortiert[highlight_index], navigation)
                continue
            return

    def _baue_ki_verlauf_browser(
        self,
        verlauf: list[KiVerlaufEintrag],
        highlight_index: int,
    ):
        liste = baue_standard_tabelle(
            titel="KI-Verlauf | Gespeicherte Antworten",
            caption="UP/DOWN Auswahl | ENTER Detail | BACK Zurueck",
        )
        liste.add_column("Nr.", style="bold cyan", justify="right", width=4)
        liste.add_column("Zeit", style="green", width=16, no_wrap=True)
        liste.add_column("Rezept", style="bold white", max_width=22, overflow="ellipsis")
        liste.add_column("Score", style="white", width=7, justify="center")
        liste.add_column("Status", style="white", width=9, no_wrap=True)
        liste.add_column("Modell", style="magenta", max_width=12, overflow="ellipsis")

        sichtbare_indizes, hat_oben, hat_unten = sichtfenster_indizes(
            anzahl_zeilen=len(verlauf),
            aktiver_index=highlight_index,
            max_zeilen=MAX_ZEILEN_KOMPAKT,
        )

        if hat_oben:
            liste.add_row("...", "...", "...", "...", "...", "...", style="dim")

        for index in sichtbare_indizes:
            eintrag = verlauf[index]
            rezept = eintrag.recipe_name or eintrag.recipe_id or "-"
            modell = eintrag.model.replace("models/", "")
            zeilen_style = HIGHLIGHT_STYLE if index == highlight_index else ""
            liste.add_row(
                str(index + 1),
                self._kurz_zeit(eintrag.created_at),
                kuerze_text(rezept, 22),
                self._score_badge(eintrag.overall_rating_1_10),
                self._status_badge(eintrag.status_snapshot),
                kuerze_text(modell, 12),
                style=zeilen_style,
            )

        if hat_unten:
            liste.add_row("...", "...", "...", "...", "...", "...", style="dim")

        preview = self._baue_ki_vorschau_tabelle(verlauf[highlight_index])
        return Group(liste, preview)

    def _baue_ki_vorschau_tabelle(self, eintrag: KiVerlaufEintrag) -> Table:
        review = eintrag.review if isinstance(eintrag.review, dict) else {}
        vorschau = baue_standard_tabelle(
            titel="Ausgewaehlte Antwort | Schnellueberblick",
            caption="Wichtige KI-Daten fuer schnelle Entscheidung",
        )
        vorschau.add_column("Feld", style="bold cyan", width=16, no_wrap=True)
        vorschau.add_column("Wert", style="white", max_width=59, overflow="ellipsis")

        summary = eintrag.summary or str(review.get("summary", "")).strip() or "-"
        vorschau.add_row("Bewertung", self._score_badge(eintrag.overall_rating_1_10))
        vorschau.add_row("Rezept", kuerze_text(eintrag.recipe_name or eintrag.recipe_id or "-", 59))
        vorschau.add_row(
            "Top-Probleme",
            kuerze_text(self._issues_kompakt(review), 59),
        )
        vorschau.add_row(
            "Fehlende Daten",
            kuerze_text(self._missing_kompakt(review), 59),
        )
        vorschau.add_row(
            "Naechste Schritte",
            kuerze_text(self._actions_kompakt(review), 59),
        )
        vorschau.add_row(
            "Ingredient-Updates",
            str(max(0, eintrag.ingredient_changes_applied)),
        )
        vorschau.add_row("Kurzfazit", kuerze_text(summary, 59))
        vorschau.add_row("Frage", kuerze_text(eintrag.user_question or "-", 59))
        return vorschau

    def _issues_kompakt(self, review: dict[str, Any]) -> str:
        issues = review.get("issues", [])
        if not isinstance(issues, list):
            return "-"
        teile: list[str] = []
        for eintrag in issues:
            if not isinstance(eintrag, dict):
                continue
            thema = str(eintrag.get("topic", "")).strip()
            schwere = str(eintrag.get("severity", "")).strip().lower()
            if not thema:
                continue
            if schwere in ("high", "medium", "low"):
                teile.append(f"{thema}({schwere})")
            else:
                teile.append(thema)
            if len(teile) >= 3:
                break
        return ", ".join(teile) if teile else "-"

    def _missing_kompakt(self, review: dict[str, Any]) -> str:
        missing = review.get("missing_data_suggestions", [])
        if not isinstance(missing, list):
            return "-"
        felder: list[str] = []
        for eintrag in missing:
            if not isinstance(eintrag, dict):
                continue
            feld = str(eintrag.get("field", "")).strip()
            if not feld:
                continue
            felder.append(feld)
            if len(felder) >= 3:
                break
        return ", ".join(felder) if felder else "-"

    def _actions_kompakt(self, review: dict[str, Any]) -> str:
        actions = review.get("next_actions", [])
        if not isinstance(actions, list):
            return "-"
        teile = [str(action).strip() for action in actions if str(action).strip()]
        if not teile:
            return "-"
        return " | ".join(teile[:2])

    def _score_badge(self, rating: int | float | None) -> str:
        try:
            wert = int(rating or 0)
        except (TypeError, ValueError):
            wert = 0
        if wert <= 0:
            return "[dim]-[/dim]"
        if wert >= 8:
            return f"[green]{wert}/10[/green]"
        if wert >= 5:
            return f"[yellow]{wert}/10[/yellow]"
        return f"[red]{wert}/10[/red]"

    def _status_badge(self, status: str | None) -> str:
        text = (status or "-").strip().lower()
        if text in ("completed", "done", "abgeschlossen"):
            return f"[green]{text}[/green]"
        if text in ("running", "active", "wartend", "paused"):
            return f"[yellow]{text}[/yellow]"
        if text in ("aborted", "cancelled", "error"):
            return f"[red]{text}[/red]"
        return text or "-"

    def _zeige_ki_verlauf_detail(
        self,
        eintrag: KiVerlaufEintrag,
        navigation,
    ) -> None:
        seiten = [
            "Uebersicht",
            "Probleme",
            "Fehlende Daten",
            "Zutaten-Vorschlaege",
        ]
        seite_index = 0
        scroll_offsets = [0, 0, 0, 0]

        def render():
            return self._baue_ki_verlauf_detail_tabelle(
                eintrag=eintrag,
                seite_index=seite_index,
                seiten=seiten,
                start_index=scroll_offsets[seite_index],
            )

        def input_handler(taste: str):
            nonlocal seite_index

            if taste == "LEFT":
                seite_index = (seite_index - 1) % len(seiten)
            elif taste == "RIGHT":
                seite_index = (seite_index + 1) % len(seiten)
            elif taste == "UP":
                if seite_index > 0:
                    scroll_offsets[seite_index] = max(0, scroll_offsets[seite_index] - 1)
            elif taste == "DOWN":
                if seite_index > 0:
                    total = self._anzahl_ki_detail_zeilen(eintrag, seite_index)
                    max_start = max(0, total - MAX_ZEILEN_STANDARD)
                    scroll_offsets[seite_index] = min(
                        max_start,
                        scroll_offsets[seite_index] + 1,
                    )
            elif taste == "r":
                with self.renderer.suspended():
                    print("\nRoh-JSON:\n")
                    print(json.dumps(eintrag.review, ensure_ascii=False, indent=2))
                    input("ENTER druecken, um zur Detailansicht zurueckzukehren...")
            elif taste in ("ENTER", "BACK", "ESC"):
                return taste
            return None

        self.renderer.render_loop(render, navigation, input_handler)

    def _anzahl_ki_detail_zeilen(self, eintrag: KiVerlaufEintrag, seite_index: int) -> int:
        review = eintrag.review if isinstance(eintrag.review, dict) else {}
        if seite_index == 1:
            issues = review.get("issues", [])
            if not isinstance(issues, list):
                return 0
            return len([issue for issue in issues if isinstance(issue, dict)])
        if seite_index == 2:
            missing = review.get("missing_data_suggestions", [])
            if not isinstance(missing, list):
                return 0
            return len([item for item in missing if isinstance(item, dict)])
        if seite_index == 3:
            return len(self._extrahiere_ingredient_suggestions(review))
        return 0

    def _baue_ki_verlauf_detail_tabelle(
        self,
        eintrag: KiVerlaufEintrag,
        seite_index: int,
        seiten: list[str],
        start_index: int = 0,
    ) -> Table:
        titel = f"KI-Verlauf | {seiten[seite_index]} ({seite_index + 1}/{len(seiten)})"
        caption = "LEFT/RIGHT Seite | UP/DOWN scrollen | r Roh-JSON | ENTER/BACK Zurueck"

        review = eintrag.review if isinstance(eintrag.review, dict) else {}

        if seite_index == 0:
            tabelle = baue_standard_tabelle(titel=titel, caption=caption)
            tabelle.add_column("Feld", style="bold cyan", width=19, no_wrap=True)
            tabelle.add_column("Wert", style="white", max_width=56, overflow="ellipsis")

            rating = (
                f"{eintrag.overall_rating_1_10}/10"
                if eintrag.overall_rating_1_10 > 0
                else "-"
            )
            tabelle.add_row("Zeitpunkt", self._kurz_zeit(eintrag.created_at))
            tabelle.add_row("Rezept", kuerze_text(eintrag.recipe_name or eintrag.recipe_id, 56))
            tabelle.add_row("Backvorgang-ID", kuerze_text(eintrag.backvorgang_id, 56))
            tabelle.add_row("Modell", kuerze_text(eintrag.model, 56))
            tabelle.add_row("Status", kuerze_text(eintrag.status_snapshot, 56))
            tabelle.add_row("Bewertung", rating)
            tabelle.add_row("Frage", kuerze_text(eintrag.user_question or "-", 56))
            tabelle.add_row("Kurzfazit", kuerze_text(eintrag.summary or "-", 56))
            tabelle.add_row(
                "Ingredient-Updates",
                str(max(0, eintrag.ingredient_changes_applied)),
            )
            tabelle.add_row(
                "In Backvorgang gespeichert",
                "ja" if eintrag.review_in_backvorgang_saved else "nein",
            )

            staerken = review.get("strengths", [])
            if isinstance(staerken, list) and staerken:
                for index, punkt in enumerate(staerken[:2], start=1):
                    tabelle.add_row(
                        f"Staerke {index}",
                        kuerze_text(str(punkt), 56),
                    )

            next_actions = review.get("next_actions", [])
            if isinstance(next_actions, list) and next_actions:
                for index, punkt in enumerate(next_actions[:2], start=1):
                    tabelle.add_row(
                        f"Naechster Schritt {index}",
                        kuerze_text(str(punkt), 56),
                    )

            return tabelle

        if seite_index == 1:
            issues = review.get("issues", [])
            tabelle = baue_standard_tabelle(titel=titel, caption=caption)
            tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
            tabelle.add_column("Thema", style="bold white", max_width=16, overflow="ellipsis")
            tabelle.add_column("Schwere", style="magenta", width=8)
            tabelle.add_column("Details", style="white", max_width=44, overflow="fold")

            if not isinstance(issues, list) or not issues:
                tabelle.add_row("-", "-", "-", "Keine Probleme gespeichert")
                return tabelle

            alle = [item for item in issues if isinstance(item, dict)]
            total = len(alle)
            max_start = max(0, total - MAX_ZEILEN_STANDARD)
            start = max(0, min(start_index, max_start))
            ende = min(total, start + MAX_ZEILEN_STANDARD)

            if start > 0:
                tabelle.add_row("...", "...", "...", "...", style="dim")

            for index, issue in enumerate(alle[start:ende], start=start + 1):
                severity = str(issue.get("severity", "")).strip().lower()
                if severity == "high":
                    severity_text = "[red]high[/red]"
                elif severity == "medium":
                    severity_text = "[yellow]medium[/yellow]"
                elif severity == "low":
                    severity_text = "[green]low[/green]"
                else:
                    severity_text = "-"

                tabelle.add_row(
                    str(index),
                    kuerze_text(str(issue.get("topic", "")), 16),
                    severity_text,
                    kuerze_text(str(issue.get("details", "")), 44),
                )

            if ende < total:
                tabelle.add_row("...", "...", "...", f"... {total - ende} weitere", style="dim")
            return tabelle

        if seite_index == 2:
            missing = review.get("missing_data_suggestions", [])
            tabelle = baue_standard_tabelle(titel=titel, caption=caption)
            tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
            tabelle.add_column("Feld", style="bold white", max_width=14, overflow="ellipsis")
            tabelle.add_column("Conf.", style="cyan", width=7)
            tabelle.add_column("Grund", style="white", max_width=20, overflow="fold")
            tabelle.add_column("Vorschlag", style="white", max_width=28, overflow="fold")

            if not isinstance(missing, list) or not missing:
                tabelle.add_row("-", "-", "-", "-", "Keine Vorschlaege")
                return tabelle

            alle = [item for item in missing if isinstance(item, dict)]
            total = len(alle)
            max_start = max(0, total - MAX_ZEILEN_STANDARD)
            start = max(0, min(start_index, max_start))
            ende = min(total, start + MAX_ZEILEN_STANDARD)

            if start > 0:
                tabelle.add_row("...", "...", "...", "...", "...", style="dim")

            for index, item in enumerate(alle[start:ende], start=start + 1):
                tabelle.add_row(
                    str(index),
                    kuerze_text(str(item.get("field", "")), 14),
                    kuerze_text(str(item.get("confidence", "-")), 7),
                    kuerze_text(str(item.get("reason", "")), 20),
                    kuerze_text(self._suggested_value_as_text(item.get("suggested_value")), 28),
                )

            if ende < total:
                tabelle.add_row("...", "...", "...", "...", f"... {total - ende} weitere", style="dim")
            return tabelle

        ingredient_vorschlaege = self._extrahiere_ingredient_suggestions(review)
        tabelle = baue_standard_tabelle(titel=titel, caption=caption)
        tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
        tabelle.add_column("Zutat", style="bold white", max_width=16, overflow="ellipsis")
        tabelle.add_column("Soll g", style="green", justify="right", width=8)
        tabelle.add_column("Ist g", style="yellow", justify="right", width=8)
        tabelle.add_column("Hinweis", style="white", max_width=38, overflow="fold")

        if not ingredient_vorschlaege:
            tabelle.add_row("-", "-", "-", "-", "Keine ingredient_usage-Vorschlaege")
            return tabelle

        total = len(ingredient_vorschlaege)
        max_start = max(0, total - MAX_ZEILEN_STANDARD)
        start = max(0, min(start_index, max_start))
        ende = min(total, start + MAX_ZEILEN_STANDARD)

        if start > 0:
            tabelle.add_row("...", "...", "...", "...", "...", style="dim")

        for index, item in enumerate(ingredient_vorschlaege[start:ende], start=start + 1):
            planned = self._to_float_oder_none(item.get("planned_g"))
            actual = self._to_float_oder_none(item.get("actual_g"))
            tabelle.add_row(
                str(index),
                kuerze_text(str(item.get("ingredient_id", "")), 16),
                self._fmt_gramm(planned),
                self._fmt_gramm(actual),
                kuerze_text(str(item.get("note", "")) or "-", 38),
            )

        if ende < total:
            tabelle.add_row("...", "...", "...", "...", f"... {total - ende} weitere", style="dim")
        return tabelle

    def _fmt_gramm(self, value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:.1f}"

    def _kurz_zeit(self, zeitstempel: str | None) -> str:
        if not zeitstempel:
            return "-"
        text = zeitstempel.replace("T", " ")
        if len(text) >= 16:
            return text[:16]
        return text

    def _modelle_anzeigen(self) -> None:
        client = self._hole_client()
        if client is None:
            return

        modellnamen: list[str] = []
        try:
            for model in client.models.list():
                name = getattr(model, "name", None)
                if isinstance(name, str) and name:
                    modellnamen.append(name)
        except Exception as exc:
            with self.renderer.suspended():
                print(f"\nModelle konnten nicht geladen werden: {exc}")
                input("ENTER druecken, um zurueckzukehren...")
            return

        with self.renderer.suspended():
            tabelle = baue_standard_tabelle(
                titel="KI-Modelle (Google GenAI)",
                caption=f"Aktuelles Modell: {self.model_name}",
            )
            tabelle.add_column("Nr.", style="bold cyan", justify="right", width=4)
            tabelle.add_column(
                "Modellname", style="bold white", no_wrap=True, overflow="ellipsis"
            )

            if not modellnamen:
                tabelle.add_row("-", "Keine Modelle gefunden")
            else:
                sichtbare = modellnamen[:MAX_ZEILEN_STANDARD]
                for index, name in enumerate(sichtbare, start=1):
                    tabelle.add_row(str(index), kuerze_text(name, 68))
                if len(modellnamen) > MAX_ZEILEN_STANDARD:
                    rest = len(modellnamen) - MAX_ZEILEN_STANDARD
                    tabelle.add_row("...", f"... {rest} weitere")

            self.renderer.console.print(tabelle)
            input("ENTER druecken, um zurueckzukehren...")

    def _backvorgang_auswaehlen(
        self, backvorgaenge: list[Backvorgang], navigation
    ) -> int | None:
        eintraege = []
        for eintrag in backvorgaenge:
            rezeptname = eintrag.recipe_snapshot.name or eintrag.recipe_id
            offene = self._zaehle_offene_schritte(eintrag)
            eintraege.append(
                f"{rezeptname} | {eintrag.id} | {eintrag.status} | offene Schritte: {offene}"
            )

        return Menu(eintraege).anzeigen(navigation, self.renderer)

    def _frage_meisterbaecker_ki(
        self,
        backvorgang: Backvorgang,
        rezept: BrotRezept | None,
        zusatzfrage: str,
    ) -> dict[str, Any] | None:
        client = self._hole_client()
        if client is None:
            return None

        backvorgang_json = json.dumps(
            backvorgang.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        rezept_json = json.dumps(
            rezept.to_dict() if rezept is not None else {},
            ensure_ascii=False,
            indent=2,
        )

        prompt = f"""
Du bist ein deutscher Meisterbaecker mit hoher Praxiserfahrung.
Analysiere den Backvorgang kritisch und gib konkrete Verbesserungen.
Antworte AUSSCHLIESSLICH als valides JSON (kein Markdown, kein Freitext davor/danach).

JSON-Struktur (genau diese Top-Level-Keys verwenden):
{{
  "persona": "meisterbaecker",
  "overall_rating_1_10": 0,
  "summary": "",
  "strengths": ["", ""],
  "issues": [
    {{"topic": "", "severity": "low|medium|high", "details": ""}}
  ],
  "missing_data_suggestions": [
    {{"field": "", "reason": "", "suggested_value": "", "confidence": "low|medium|high"}}
  ],
  "ingredient_usage_suggestions": [
    {{"ingredient_id": "", "planned_g": 0, "actual_g": 0, "note": ""}}
  ],
  "next_actions": ["", ""]
}}

Regeln:
- Wenn Daten fehlen, liefere sinnvolle Vorschlaege in "missing_data_suggestions".
- Nutze nur plausible Baeckerlogik, keine Fantasie.
- "overall_rating_1_10" ist ganzzahlig zwischen 1 und 10.
- Antworte kompakt: max 3 "strengths", max 6 "issues", max 5 "missing_data_suggestions", max 5 "next_actions".
- Jede "issues.details" kurz halten (max ~220 Zeichen).

BACKVORGANG_JSON:
{backvorgang_json}

REZEPT_JSON:
{rezept_json}

ZUSATZFRAGE:
{zusatzfrage or "-"}
"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": 0.2,
                    "max_output_tokens": 1600,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:
            with self.renderer.suspended():
                print(f"\nKI-Anfrage fehlgeschlagen: {exc}")
                input("ENTER druecken, um zurueckzukehren...")
            return None

        daten = response.parsed if isinstance(response.parsed, dict) else None
        text = getattr(response, "text", None)

        if daten is None and isinstance(text, str) and text.strip():
            daten = self._parse_json_antwort(text)

        if daten is None and isinstance(text, str) and text.strip():
            daten = self._repariere_json_antwort(client, text)

        if daten is None:
            with self.renderer.suspended():
                print("\nKI-Antwort konnte nicht als JSON gelesen werden.")
                print("Rohantwort:\n")
                print(text or "-")
                input("\nENTER druecken, um zurueckzukehren...")
            return None

        return self._normalisiere_review_json(daten)

    def _parse_json_antwort(self, text: str) -> dict[str, Any] | None:
        kandidaten: list[str] = []
        roh = text.strip()
        kandidaten.append(roh)

        if roh.startswith("```"):
            ohne_start = roh.replace("```json", "", 1).replace("```", "").strip()
            kandidaten.append(ohne_start)

        extrahiert = self._extrahiere_erstes_json_objekt(roh)
        if extrahiert:
            kandidaten.append(extrahiert)

        for kandidat in kandidaten:
            try:
                daten = json.loads(kandidat)
            except json.JSONDecodeError:
                continue
            if isinstance(daten, dict):
                return daten

        return None

    def _extrahiere_erstes_json_objekt(self, text: str) -> str | None:
        start = text.find("{")
        if start < 0:
            return None

        tiefe = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            zeichen = text[index]

            if in_string:
                if escaped:
                    escaped = False
                elif zeichen == "\\":
                    escaped = True
                elif zeichen == '"':
                    in_string = False
                continue

            if zeichen == '"':
                in_string = True
                continue

            if zeichen == "{":
                tiefe += 1
            elif zeichen == "}":
                tiefe -= 1
                if tiefe == 0:
                    return text[start : index + 1]

        return None

    def _repariere_json_antwort(
        self,
        client: genai.Client,
        rohantwort: str,
    ) -> dict[str, Any] | None:
        prompt = f"""
Konvertiere die folgende KI-Rohantwort in EIN valides JSON-Objekt.
Entferne Markdown-Fences und unvollstaendige Fragmente.
Nutze diese Top-Level-Keys:
persona, overall_rating_1_10, summary, strengths, issues,
missing_data_suggestions, ingredient_usage_suggestions, next_actions.
Wenn ein Bereich fehlt, nutze leere Standardwerte.
Antworte nur mit JSON.

ROHANTWORT:
{rohantwort}
"""
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": 0.0,
                    "max_output_tokens": 1400,
                    "response_mime_type": "application/json",
                },
            )
        except Exception:
            return None

        if isinstance(response.parsed, dict):
            return response.parsed

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return self._parse_json_antwort(text)
        return None

    def _normalisiere_review_json(self, daten: dict[str, Any]) -> dict[str, Any]:
        rating = daten.get("overall_rating_1_10")
        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            rating_int = 0
        rating_int = max(1, min(10, rating_int)) if rating_int else 0

        def as_list_text(key: str) -> list[str]:
            rohwert = daten.get(key, [])
            if not isinstance(rohwert, list):
                return []
            return [str(eintrag) for eintrag in rohwert if str(eintrag).strip()]

        def as_list_dict(key: str) -> list[dict[str, Any]]:
            rohwert = daten.get(key, [])
            if not isinstance(rohwert, list):
                return []
            return [eintrag for eintrag in rohwert if isinstance(eintrag, dict)]

        return {
            "persona": "meisterbaecker",
            "overall_rating_1_10": rating_int,
            "summary": str(daten.get("summary", "")).strip(),
            "strengths": as_list_text("strengths"),
            "issues": as_list_dict("issues"),
            "missing_data_suggestions": as_list_dict("missing_data_suggestions"),
            "ingredient_usage_suggestions": as_list_dict("ingredient_usage_suggestions"),
            "next_actions": as_list_text("next_actions"),
        }

    def _zeige_review_kompakt(self, review: dict[str, Any]) -> None:
        rating = int(review.get("overall_rating_1_10") or 0)
        if rating >= 8:
            border = "green"
        elif rating >= 5:
            border = "yellow"
        else:
            border = "red"

        summary_panel = Panel(
            (
                f"[bold]Meisterbaecker-Score:[/bold] {rating}/10\n"
                f"[bold]Kurzfazit:[/bold] {kuerze_text(review.get('summary', ''), 500)}"
            ),
            title="[bold bright_white]KI-Bewertung[/bold bright_white]",
            border_style=border,
        )

        issues_table = baue_standard_tabelle(titel="Kernprobleme", caption="Top-6")
        issues_table.add_column("Thema", style="bold white", max_width=18, overflow="ellipsis")
        issues_table.add_column("Schwere", style="magenta", width=8)
        issues_table.add_column("Details", style="white", max_width=46, overflow="ellipsis")
        issues = review.get("issues", [])
        if isinstance(issues, list) and issues:
            for eintrag in issues[:6]:
                if not isinstance(eintrag, dict):
                    continue
                severity = str(eintrag.get("severity", "")).strip().lower()
                if severity == "high":
                    severity_text = "[red]high[/red]"
                elif severity == "medium":
                    severity_text = "[yellow]medium[/yellow]"
                elif severity == "low":
                    severity_text = "[green]low[/green]"
                else:
                    severity_text = "-"
                issues_table.add_row(
                    kuerze_text(str(eintrag.get("topic", "")), 18),
                    severity_text,
                    kuerze_text(str(eintrag.get("details", "")), 46),
                )
        else:
            issues_table.add_row("-", "-", "Keine Auffaelligkeiten gemeldet")

        missing_table = baue_standard_tabelle(
            titel="Fehlende Daten (Vorschlaege)",
            caption="Top-5",
        )
        missing_table.add_column("Feld", style="bold white", max_width=18, overflow="ellipsis")
        missing_table.add_column("Confidence", style="cyan", width=11)
        missing_table.add_column("Vorschlag", style="white", max_width=43, overflow="ellipsis")
        missing = review.get("missing_data_suggestions", [])
        if isinstance(missing, list) and missing:
            for eintrag in missing[:5]:
                if not isinstance(eintrag, dict):
                    continue
                missing_table.add_row(
                    kuerze_text(str(eintrag.get("field", "")), 18),
                    kuerze_text(str(eintrag.get("confidence", "-")), 11),
                    kuerze_text(self._suggested_value_as_text(eintrag.get("suggested_value")), 43),
                )
        else:
            missing_table.add_row("-", "-", "Keine fehlenden Daten erkannt")

        actions = review.get("next_actions", [])
        actions_text = "- " + "\n- ".join(actions[:5]) if isinstance(actions, list) and actions else "- Keine"
        actions_panel = Panel(
            actions_text,
            title="[bold bright_white]Naechste Schritte[/bold bright_white]",
            border_style="grey50",
        )

        with self.renderer.suspended():
            self.renderer.console.print(Group(summary_panel, issues_table, missing_table, actions_panel))

    def _suggested_value_as_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, dict):
            return ", ".join(str(k) for k in list(value.keys())[:4]) or "-"
        if isinstance(value, list):
            return f"Liste mit {len(value)} Eintraegen"
        return "-"

    def _wende_ingredient_suggestions_an(
        self,
        backvorgang: Backvorgang,
        review: dict[str, Any],
    ) -> int:
        aenderungen = self._ermittle_ingredient_suggestion_aenderungen(backvorgang, review)
        return self._wende_ingredient_aenderungen_an(backvorgang, aenderungen)

    def _ermittle_ingredient_suggestion_aenderungen(
        self,
        backvorgang: Backvorgang,
        review: dict[str, Any],
    ) -> list[dict[str, Any]]:
        vorschlaege = self._extrahiere_ingredient_suggestions(review)
        if not vorschlaege:
            return []

        bestehend_index = {
            (eintrag.mehl_id or "").lower(): eintrag
            for eintrag in backvorgang.ingredient_usage
        }
        gesammelt: dict[str, dict[str, Any]] = {}

        for vorschlag in vorschlaege:
            ingredient_id = (vorschlag.get("ingredient_id") or "").strip()
            if not ingredient_id:
                continue

            key = ingredient_id.lower()
            planned = self._to_float_oder_none(vorschlag.get("planned_g"))
            actual = self._to_float_oder_none(vorschlag.get("actual_g"))

            if key not in gesammelt:
                alt = bestehend_index.get(key)
                old_planned = alt.planned_g if alt is not None else None
                old_actual = alt.actual_g if alt is not None else None
                gesammelt[key] = {
                    "ingredient_id": alt.mehl_id if alt is not None else ingredient_id,
                    "mode": "update" if alt is not None else "add",
                    "old_planned_g": old_planned,
                    "new_planned_g": (
                        round(max(0.0, old_planned), 3) if old_planned is not None else 0.0
                    ),
                    "old_actual_g": old_actual,
                    "new_actual_g": (
                        round(max(0.0, old_actual), 3) if old_actual is not None else 0.0
                    ),
                }

            if planned is not None:
                gesammelt[key]["new_planned_g"] = round(max(0.0, planned), 3)
            if actual is not None:
                gesammelt[key]["new_actual_g"] = round(max(0.0, actual), 3)

        aenderungen: list[dict[str, Any]] = []
        for eintrag in gesammelt.values():
            old_planned = eintrag.get("old_planned_g")
            old_actual = eintrag.get("old_actual_g")
            if eintrag["mode"] == "add":
                aenderungen.append(eintrag)
                continue

            planned_changed = (
                old_planned is None or round(float(old_planned), 3) != eintrag["new_planned_g"]
            )
            actual_changed = (
                old_actual is None or round(float(old_actual), 3) != eintrag["new_actual_g"]
            )
            if planned_changed or actual_changed:
                aenderungen.append(eintrag)

        return sorted(aenderungen, key=lambda x: str(x.get("ingredient_id", "")).lower())

    def _zeige_ingredient_diff_vorschau(self, aenderungen: list[dict[str, Any]]) -> None:
        tabelle = baue_standard_tabelle(
            titel="KI-Vorschau | ingredient_usage Diff",
            caption="Alt -> Neu (nur geaenderte Eintraege)",
        )
        tabelle.add_column("Zutat", style="bold white", max_width=18, overflow="ellipsis")
        tabelle.add_column("Aktion", style="cyan", width=8)
        tabelle.add_column("Soll alt", style="green", justify="right", width=8)
        tabelle.add_column("Soll neu", style="green", justify="right", width=8)
        tabelle.add_column("Ist alt", style="yellow", justify="right", width=8)
        tabelle.add_column("Ist neu", style="yellow", justify="right", width=8)

        sichtbare = aenderungen[:MAX_ZEILEN_STANDARD]
        for eintrag in sichtbare:
            def _fmt(v: Any) -> str:
                if v is None:
                    return "-"
                return f"{float(v):.1f}"

            tabelle.add_row(
                kuerze_text(str(eintrag.get("ingredient_id", "")), 18),
                str(eintrag.get("mode", "-")),
                _fmt(eintrag.get("old_planned_g")),
                _fmt(eintrag.get("new_planned_g")),
                _fmt(eintrag.get("old_actual_g")),
                _fmt(eintrag.get("new_actual_g")),
            )

        if len(aenderungen) > MAX_ZEILEN_STANDARD:
            rest = len(aenderungen) - MAX_ZEILEN_STANDARD
            tabelle.add_row("...", f"+{rest}", "-", "-", "-", "-", style="dim")

        with self.renderer.suspended():
            self.renderer.console.print(tabelle)

    def _wende_ingredient_aenderungen_an(
        self,
        backvorgang: Backvorgang,
        aenderungen: list[dict[str, Any]],
    ) -> int:
        if not aenderungen:
            return 0

        index = {
            (eintrag.mehl_id or "").lower(): eintrag
            for eintrag in backvorgang.ingredient_usage
        }
        anzahl = 0

        for aenderung in aenderungen:
            ingredient_id = str(aenderung.get("ingredient_id", "")).strip()
            if not ingredient_id:
                continue

            planned = self._to_float_oder_none(aenderung.get("new_planned_g"))
            actual = self._to_float_oder_none(aenderung.get("new_actual_g"))

            ziel = index.get(ingredient_id.lower())
            if ziel is None:
                ziel = ZutatenVerbrauch(
                    mehl_id=ingredient_id,
                    planned_g=max(0.0, planned) if planned is not None else 0.0,
                    actual_g=max(0.0, actual) if actual is not None else 0.0,
                    stock_deducted_g=max(0.0, actual) if actual is not None else 0.0,
                )
                backvorgang.ingredient_usage.append(ziel)
                index[ingredient_id.lower()] = ziel
                anzahl += 1
                continue

            geaendert = False
            if planned is not None:
                ziel.planned_g = round(max(0.0, planned), 3)
                geaendert = True
            if actual is not None:
                ziel.actual_g = round(max(0.0, actual), 3)
                ziel.stock_deducted_g = round(max(0.0, actual), 3)
                geaendert = True
            if geaendert:
                anzahl += 1

        return anzahl

    def _extrahiere_ingredient_suggestions(self, review: dict[str, Any]) -> list[dict[str, Any]]:
        gesammelt: list[dict[str, Any]] = []

        direkte = review.get("ingredient_usage_suggestions", [])
        if isinstance(direkte, list):
            for eintrag in direkte:
                if not isinstance(eintrag, dict):
                    continue
                gesammelt.append(
                    {
                        "ingredient_id": str(
                            eintrag.get("ingredient_id")
                            or eintrag.get("mehl_id")
                            or ""
                        ).strip(),
                        "planned_g": eintrag.get("planned_g"),
                        "actual_g": eintrag.get("actual_g"),
                        "note": str(eintrag.get("note", "")).strip(),
                    }
                )

        missing = review.get("missing_data_suggestions", [])
        if isinstance(missing, list):
            for eintrag in missing:
                if not isinstance(eintrag, dict):
                    continue
                feld = str(eintrag.get("field", "")).strip().lower()
                if feld != "ingredient_usage":
                    continue
                sv = eintrag.get("suggested_value")
                if not isinstance(sv, list):
                    continue
                for kandidat in sv:
                    if not isinstance(kandidat, dict):
                        continue
                    gesammelt.append(
                        {
                            "ingredient_id": str(
                                kandidat.get("ingredient_id")
                                or kandidat.get("mehl_id")
                                or ""
                            ).strip(),
                            "planned_g": kandidat.get("planned_g"),
                            "actual_g": kandidat.get("actual_g"),
                            "note": str(kandidat.get("note", "")).strip(),
                        }
                    )

        return gesammelt

    def _speichere_ki_review(
        self,
        backvorgaenge: list[Backvorgang],
        index: int,
        review: dict[str, Any],
    ) -> None:
        ziel = backvorgaenge[index]
        review_eintrag = {
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "model": self.model_name,
            "review": review,
        }
        bestehend = ziel.custom.get("ki_reviews")
        if isinstance(bestehend, list):
            bestehend.append(review_eintrag)
        else:
            ziel.custom["ki_reviews"] = [review_eintrag]

    def _hole_rezept(self, rezept_id: str) -> BrotRezept | None:
        rezepte = self.rezeptManager.laden(BrotRezept)
        for rezept in rezepte:
            if rezept.id == rezept_id:
                return rezept
        return None

    def _to_float_oder_none(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip().replace(",", ".")
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                return None
        return None

    def _zaehle_offene_schritte(self, backvorgang: Backvorgang) -> int:
        return sum(
            1
            for schritt in backvorgang.step_runs
            if schritt.actual_end_at is None and schritt.actual_duration_min is None
        )
