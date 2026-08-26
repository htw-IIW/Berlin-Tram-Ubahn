#!/usr/bin/env python3
"""Exportiert die Diagramme aus den Notebooks als PNG für den Videoschnitt.

Die Notebooks werden unverändert ausgeführt; `plotly.graph_objects.Figure.show`
ist dabei so umgebogen, dass jede Figur zusätzlich als PNG geschrieben wird.
Dadurch entspricht der Export immer dem, was das Notebook tatsächlich erzeugt —
es gibt keine zweite, nachgebaute Zeichenlogik, die auseinanderlaufen könnte.

Zwei Phasen:

1. **Ausführen** — alle Figuren landen in ``video/bild/diagramme/`` plus ein
   Manifest (``manifest.json``) mit Titeln und Achsenbeschriftungen.
2. **Benennen** — aus dem Manifest werden die im Storyboard gebrauchten Figuren
   herausgesucht und unter ``video/bild/szeneN_*.png`` abgelegt.

Phase 2 lässt sich mit ``--nur-benennen`` allein wiederholen, ohne die
Notebooks erneut zu rechnen (ein voller Lauf dauert rund 12 Minuten).

    python scripts/export_grafiken.py                 # beides
    python scripts/export_grafiken.py --nur-benennen  # nur Zuordnung
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
NOTEBOOK_ORDNER = WURZEL / "notebooks"
ZIEL = WURZEL / "video" / "bild"
DIAGRAMME = ZIEL / "diagramme"
RESERVE_ORDNER = ZIEL / "reserve"
MANIFEST = DIAGRAMME / "manifest.json"

# Videoformat. Die Grafiken werden formatfüllend gezeigt, nicht als
# verkleinertes Overlay — bei 72 dpi sind Achsenbeschriftungen unlesbar.
BREITE, HOEHE = 1920, 1080

# Titel, die im Video anders lauten sollen als im Notebook.
#
# Im Notebook darf ein Titel erklären — dort liest jemand mit und hat Zeit.
# Im Video konkurriert jedes zusätzliche Wort mit dem gesprochenen Text und
# wird nicht gelesen. Erklärende Unterzeilen (`<br><sub>…`) entfallen damit
# automatisch, weil der Titel vollständig ersetzt wird.
#
# Schlüssel: Teilstring des Originaltitels, klein geschrieben.
# Wert: der Titel, der ins Bild kommt.
#
# Das Notebook bleibt unberührt — die Änderung gilt nur für den PNG-Export.
TITEL_IM_VIDEO = {
    "erzeugte verspätung im zulauf": "Erzeugte Verspätung je LSA-Status",
}

# Dasselbe für Kategorienamen an den Achsen und in der Legende. Ersetzt wird
# als Teilstring, damit Zusätze wie "<br>(n=4)" erhalten bleiben.
# Achtung bei der Reihenfolge: Es wird als Teilstring ersetzt. "inaktiv (laut
# Drucksache)" enthält "aktiv" — deshalb hier keine Regel für "aktiv" ergänzen,
# ohne die Ersetzung auf ganze Namen umzustellen.
BESCHRIFTUNG_IM_VIDEO = {
    # Derzeit leer: Die Gruppennamen im Notebook sind seit der Umstellung auf
    # "Beeinflussung" (Terminologie des Senats, Drs. 19/19804, Antwort 8/9)
    # schon videotauglich. Der Mechanismus bleibt für spätere Fälle stehen.
}

NOTEBOOKS = [
    "01_eda.ipynb",
    "02_eda.ipynb",
    "03_lsa_analyse.ipynb",
    "04_hypothesen.ipynb",
    "04_delay_propagation.ipynb",
    "05_massnahmen.ipynb",
]

# Storyboard-Szene -> (Notebook, Suchbegriff in Titel/Achsen/Annotationen).
# Der Suchbegriff wird klein geschrieben verglichen; der erste Treffer gewinnt.
SZENEN = {
    # Boxplot statt Balken: Bei sechs belegten inaktiven Anlagen muss die
    # Gruppengröße mit im Bild stehen, sonst liest man den Median als sicherer,
    # als er ist. Die Balkenfassung derselben Zahlen gibt es deshalb nicht mehr.
    "szene3_lsa_gruppen":      ("03_lsa_analyse", "erzeugte verspätung im zulauf"),
    # Beantwortet die Frage, warum man auf der LSA-Karte keine Ursache sieht:
    # mittlere und erzeugte Verspätung hängen kaum zusammen.
    "szene3c_erben_erzeugen":  ("03_lsa_analyse", "heißt nicht, dass sie dort entsteht"),
    "szene4_effektstaerken":   ("02_eda", "rang-biseriale"),
    "szene5_puenktlichkeit":   ("01_eda", "pünktlichkeitsfenster"),
    # Verfrühungen gegen Verspätungen an einer gemeinsamen Nulllinie, ohne den
    # pünktlichen Rest. Läuft im Storyboard vor der amtlichen rbb-Grafik.
    #
    # Bewusst OHNE Szenennummer: Die Nummern in diesem Wörterbuch stammen aus
    # der Zeit vor der Umstellung vom 09.08.2026 und stimmen nicht mehr
    # (szene3b_lsa_balken gehört inzwischen zu Szene 6). Eine weitere, diesmal
    # richtige Nummer daneben wäre die schlechtere Verwirrung. Die Zuordnung
    # Grafik → Szene steht in PRESENTATION.md, Abschnitt „Grafiken".
    "richtungen_frueh_spaet":  ("01_eda", "in beide richtungen häufiger ab"),
    "szene6_konzentration":    ("04_delay_propagation", "anteil der abschnitte"),
    "szene6b_ueberlappung":    ("02_eda", "netze überlappen"),
    "szene7_massnahmen":       ("05_massnahmen", "personenstunden"),
}

# Optional, für die im Audit vorgeschlagenen Ergänzungen.
KUER = {
    "extra_n_inflation":        ("04_hypothesen", "stichprobe"),
    "extra_collector_ausfall":  ("01_eda", "erhebungsvolumen"),
    "extra_modell_guete":       ("05_massnahmen", "vorhergesagte wahrscheinlichkeit"),
    "extra_entscheidungshilfe": ("05_massnahmen", "verspätungsrisiko nach linie"),
}

# Rückhand für die Fragerunde: Diagramme, die eine absehbare Nachfrage
# beantworten oder eine Szene notfalls ersetzen können. Landen in
# video/bild/reserve/. Alles andere bleibt im Notebook — dort steht es im
# Zusammenhang, und im Schnittprogramm wäre es nur Ballast.
# Dass der LSA-Befund spezifisch für die Fahrzeit ist und sich nicht im Ausfall
# zeigt, steht als Rechnung und Ergebnis in Notebook 03, Abschnitt 4d, Teil 2 —
# eine eigene Grafik dafür gibt es nicht, die Zahlen genügen für die Nachfrage.
RESERVE = {
    "schwellenabstand":     ("01_eda", "je schwelle"),
    "takt_und_verfruehung": ("01_eda", "verfrühungsrate, takt"),
    "top_abschnitte":       ("04_delay_propagation", "größten netzweiten wirkung"),
    "lage_statt_trasse":    ("04_hypothesen", "sondern die lage im netz"),
}


# --------------------------------------------------------------------------
# Phase 1 — Notebooks ausführen und jede Figur mitschreiben
# --------------------------------------------------------------------------

# Wird als erste Zelle in jedes Notebook eingesetzt. Läuft vor allen Imports
# des Notebooks; das ist unkritisch, weil die Klasse gepatcht wird und nicht
# ein bereits importierter Name.
PREAMBLE = r'''
import json as _json, os as _os, re as _re
from pathlib import Path as _Path
import plotly.graph_objects as _go

_ZIEL   = _Path(_os.environ["EXPORT_ZIEL"])
_STEM   = _os.environ["EXPORT_STEM"]
_BREITE = int(_os.environ["EXPORT_BREITE"])
_HOEHE  = int(_os.environ["EXPORT_HOEHE"])
_TITEL_IM_VIDEO = _json.loads(_os.environ.get("EXPORT_TITEL_IM_VIDEO", "{}"))
_BESCHRIFTUNG_IM_VIDEO = _json.loads(_os.environ.get("EXPORT_BESCHRIFTUNG_IM_VIDEO", "{}"))
_zaehler = {"n": 0}
_eintraege = []

def _text(x):
    return "" if x is None else str(x)

def _slug(s):
    s = _re.sub(r"<[^>]+>", " ", s)          # <br>, <sub> aus Titeln entfernen
    s = (s.replace("ä","ae").replace("ö","oe").replace("ü","ue")
           .replace("Ä","Ae").replace("Ö","Oe").replace("Ü","Ue").replace("ß","ss"))
    s = _re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return (s[:60] or "figur")

def _beschriftungen(fig):
    """Titel, Achsentitel und Annotationen — das Suchfeld für die Zuordnung."""
    teile = [_text(fig.layout.title.text)]
    for name in dir(fig.layout):
        if _re.fullmatch(r"[xy]axis\d*", name):
            achse = getattr(fig.layout, name, None)
            if achse is not None and getattr(achse, "title", None) is not None:
                teile.append(_text(achse.title.text))
    for ann in (fig.layout.annotations or []):
        teile.append(_text(ann.text))
    return [t for t in teile if t]

def _titel_fuers_video(fig):
    """Titel ersetzen, wo im Video eine kürzere Fassung gewünscht ist."""
    titel = _text(fig.layout.title.text)
    if not titel:
        return fig
    klein = titel.lower()
    for suchbegriff, ersatz in _TITEL_IM_VIDEO.items():
        if suchbegriff in klein:
            fig.layout.title.text = ersatz
            break
    return fig

def _beschriftungen_ersetzen(fig):
    """Kategorienamen fuers Video umbenennen (Achsen, Legende)."""
    if not _BESCHRIFTUNG_IM_VIDEO:
        return fig

    def ersetzen(t):
        for alt, neu in _BESCHRIFTUNG_IM_VIDEO.items():
            if alt in t:
                t = t.replace(alt, neu)
        return t

    for spur in fig.data:
        if getattr(spur, "name", None):
            spur.name = ersetzen(spur.name)
        # Bei Balken stehen die Kategorien in x, nicht im Trace-Namen.
        werte = getattr(spur, "x", None)
        if werte is not None and len(werte) and isinstance(werte[0], str):
            spur.x = [ersetzen(w) for w in werte]
    for name in dir(fig.layout):
        if _re.fullmatch(r"[xy]axis\d*", name):
            achse = getattr(fig.layout, name, None)
            if achse is not None and getattr(achse, "ticktext", None):
                achse.ticktext = [ersetzen(_text(t)) for t in achse.ticktext]
    return fig

def _annotationen_einfangen(fig):
    """Beschriftungen am rechten Plotrand nach innen ziehen.

    add_hline(..., annotation_position="right") legt den Text mit x=1 und
    xanchor="left" ab — er beginnt also an der Kante der Zeichenflaeche und
    laeuft nach aussen. Im Notebook faellt das nicht auf, weil die Grafik
    mitwaechst. Beim PNG-Export mit fester Breite wird er abgeschnitten, und
    zwar umso mehr, je groesser die Schrift ist. Ein breiterer Rand hilft
    nicht: Der Text waechst mit.

    Auf x wird nur geprueft, wenn dort wirklich eine Zahl steht. Bei einer
    Zeitachse ist ann.x ein Datum (add_vrect setzt es so), und ein Vergleich
    mit 1 wirft einen TypeError. Der landete im Auffangblock von
    _show_und_speichern und liess die Grafik still verschwinden.
    """
    neu = []
    for ann in (fig.layout.annotations or []):
        x = ann.x
        ist_relativ = isinstance(x, (int, float)) and not isinstance(x, bool)
        if getattr(ann, "xanchor", None) == "left" and ist_relativ and x >= 1:
            ann.xanchor = "right"
        neu.append(ann)
    if neu:
        fig.layout.annotations = neu
    return fig

def _lesbar_machen(fig):
    """Schriftgrößen für die Projektion anheben. Farben bleiben unberührt.

    Die Umrechnung selbst steht seit dem 09.08.2026 in
    src/analysis/grafiken.fuers_video, damit scripts/grafik_richtungen.py sie
    mitbenutzen kann statt einer zweiten, nachgebauten Fassung.

    Der Import ist mit Absicht verzögert: Dieser Vorspann läuft VOR allen
    Importen des Notebooks, die Projektwurzel liegt zu diesem Zeitpunkt also noch
    nicht im sys.path. Aufgerufen wird die Funktion erst beim ersten fig.show(),
    und da hat die Setup-Zelle des Notebooks den Pfad längst gesetzt.
    """
    from src.analysis.grafiken import fuers_video
    return fuers_video(fig)

_original_show = _go.Figure.show

def _show_und_speichern(self, *a, **kw):
    _zaehler["n"] += 1
    n = _zaehler["n"]
    beschriftungen = _beschriftungen(self)
    titel = beschriftungen[0] if beschriftungen else ""
    datei = _ZIEL / f"{_STEM}_{n:02d}_{_slug(titel)}.png"
    try:
        # Reihenfolge zählt: beschriftungen sind oben schon erfasst, damit das
        # Manifest den vollständigen Originaltitel behält und die Zuordnung
        # weiterhin darauf greift — gekürzt wird nur, was ins Bild geht.
        _lesbar_machen(_annotationen_einfangen(
            _beschriftungen_ersetzen(_titel_fuers_video(self)))).write_image(
                str(datei), width=_BREITE, height=_HOEHE, scale=1)
        _eintraege.append({
            "notebook": _STEM, "nr": n, "datei": datei.name,
            "titel": titel, "beschriftungen": beschriftungen,
        })
        print(f"   [png] {datei.name}")
    except Exception as e:                                   # noqa: BLE001
        print(f"   [!!!] Figur {n} nicht exportiert: {type(e).__name__}: {e}")
    (_ZIEL / f"_teil_{_STEM}.json").write_text(
        _json.dumps(_eintraege, ensure_ascii=False, indent=2), encoding="utf-8")
    return None   # kein show() im Batchlauf — spart Zeit und Speicher

_go.Figure.show = _show_und_speichern
print(f"[export] Figuren-Mitschnitt aktiv für {_STEM}")
'''


def ausfuehren(nur: list[str] | None = None) -> None:
    """Führt die Notebooks aus. `nur` beschränkt auf einzelne Dateinamen.

    Bei einem Teillauf bleiben die Manifest-Einträge der übrigen Notebooks
    erhalten, damit die Zuordnung anschließend trotzdem vollständig ist.
    """
    import nbformat
    from nbclient import NotebookClient

    DIAGRAMME.mkdir(parents=True, exist_ok=True)
    for alt in DIAGRAMME.glob("_teil_*.json"):
        alt.unlink()

    # Nach einem --aufraeumen liegt das Manifest eine Ebene höher. Für einen
    # Teillauf wird es zurückgeholt, sonst gingen die Einträge der nicht
    # gelaufenen Notebooks verloren.
    if not MANIFEST.exists() and (ZIEL / "manifest.json").exists():
        shutil.copy2(ZIEL / "manifest.json", MANIFEST)

    bestand: list[dict] = []
    if nur and MANIFEST.exists():
        stems = {Path(n).stem for n in nur}
        bestand = [e for e in json.loads(MANIFEST.read_text(encoding="utf-8"))
                   if e["notebook"] not in stems]

    os.environ.update(
        EXPORT_ZIEL=str(DIAGRAMME),
        EXPORT_BREITE=str(BREITE),
        EXPORT_HOEHE=str(HOEHE),
        EXPORT_TITEL_IM_VIDEO=json.dumps(dict(TITEL_IM_VIDEO)),
        EXPORT_BESCHRIFTUNG_IM_VIDEO=json.dumps(dict(BESCHRIFTUNG_IM_VIDEO)),
    )

    gesamt_start = time.time()
    fehler: list[str] = []

    for name in NOTEBOOKS:
        if nur and name not in nur:
            continue
        pfad = NOTEBOOK_ORDNER / name
        if not pfad.exists():
            print(f"[übersprungen] {name} nicht vorhanden")
            continue

        stem = pfad.stem
        os.environ["EXPORT_STEM"] = stem
        print(f"\n=== {name} ===", flush=True)
        start = time.time()

        nb = nbformat.read(pfad, as_version=4)
        nb.cells.insert(0, nbformat.v4.new_code_cell(PREAMBLE))

        client = NotebookClient(
            nb,
            timeout=1800,
            kernel_name="python3",
            allow_errors=False,
            resources={"metadata": {"path": str(NOTEBOOK_ORDNER)}},
        )
        try:
            client.execute()
            print(f"    fertig in {time.time() - start:.0f} s", flush=True)
            # Eine einzelne Figur kann scheitern, ohne dass das Notebook
            # abbricht — _show_und_speichern faengt die Ausnahme ab. Diese
            # Meldung steht dann nur im Ausgabestrom des Kernels und war
            # bisher unsichtbar: Die Grafik fehlte still im Manifest.
            for zelle in nb.cells:
                for ausgabe in zelle.get("outputs", []):
                    for zeile in str(ausgabe.get("text", "")).splitlines():
                        if "[!!!]" in zeile:
                            fehler.append(f"{name}: {zeile.strip()}")
                            print(f"   {zeile.strip()}", flush=True)
        except Exception as e:                               # noqa: BLE001
            fehler.append(f"{name}: {type(e).__name__}: {e}")
            print(f"    ABBRUCH nach {time.time() - start:.0f} s: {e}", flush=True)

    # Teilmanifeste zusammenführen, Bestand aus nicht gelaufenen Notebooks behalten
    eintraege: list[dict] = list(bestand)
    for teil in sorted(DIAGRAMME.glob("_teil_*.json")):
        eintraege.extend(json.loads(teil.read_text(encoding="utf-8")))
        teil.unlink()
    MANIFEST.write_text(json.dumps(eintraege, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(eintraege)} Figuren in {time.time() - gesamt_start:.0f} s")
    if fehler:
        print("\nFehler:")
        for f in fehler:
            print("  -", f)


# --------------------------------------------------------------------------
# Phase 2 — Szenen-Grafiken aus dem Manifest benennen
# --------------------------------------------------------------------------

def benennen(aufraeumen: bool = False) -> int:
    if not MANIFEST.exists():
        print(f"Kein Manifest unter {MANIFEST} — erst ohne --nur-benennen laufen lassen.")
        return 1

    eintraege = json.loads(MANIFEST.read_text(encoding="utf-8"))
    offen: list[str] = []
    benutzt: set[str] = set()

    auftrag = [(ZIEL, SZENEN), (ZIEL, KUER), (RESERVE_ORDNER, RESERVE)]
    for zielordner, gruppe in auftrag:
        for ziel, (notebook, suchbegriff) in gruppe.items():
            treffer = next(
                (e for e in eintraege
                 if e["notebook"] == notebook
                 and any(suchbegriff in b.lower() for b in e["beschriftungen"])),
                None,
            )
            if treffer is None:
                offen.append(f"{ziel}: '{suchbegriff}' in {notebook} nicht gefunden")
                continue
            quelle = DIAGRAMME / treffer["datei"]
            if not quelle.exists():
                # Nach einem Teillauf fehlen die Rohdateien der nicht
                # gelaufenen Notebooks. Liegt das Ziel schon vor, ist es
                # aktuell — nur wenn beides fehlt, ist es ein Fehler.
                if (zielordner / f"{ziel}.png").exists():
                    print(f"  {ziel}.png  unverändert")
                    continue
                offen.append(f"{ziel}: {treffer['datei']} fehlt auf der Platte")
                continue
            zielordner.mkdir(parents=True, exist_ok=True)
            shutil.copy2(quelle, zielordner / f"{ziel}.png")
            benutzt.add(treffer["datei"])
            wohin = "reserve/" if zielordner is RESERVE_ORDNER else ""
            print(f"  {wohin}{ziel}.png  ←  {treffer['titel'][:60]}")

    if aufraeumen and not offen:
        # Die Rohdateien haben ihren Zweck erfüllt: Was gebraucht wird, liegt
        # unter sprechendem Namen in video/bild/ bzw. reserve/. Der Rest bleibt
        # im Notebook, wo er im Zusammenhang steht. Das Manifest wandert mit
        # nach oben, damit nachvollziehbar bleibt, welche Diagramme es gibt.
        entfernt = 0
        for png in DIAGRAMME.glob("*.png"):
            png.unlink()
            entfernt += 1
        if MANIFEST.exists():
            shutil.move(str(MANIFEST), str(ZIEL / "manifest.json"))
        try:
            DIAGRAMME.rmdir()
        except OSError as e:
            print(f"  Hinweis: {DIAGRAMME.name}/ nicht leer, bleibt bestehen ({e})")
        print(f"\n  aufgeräumt: {entfernt} Rohdateien entfernt, "
              f"Manifest nach {ZIEL.name}/manifest.json verschoben")
        print("  (ein erneuter Lauf ohne --nur-benennen stellt sie wieder her)")

    if offen:
        print("\nNicht zugeordnet:")
        for o in offen:
            print("  -", o)
        print("\nVerfügbare Titel je Notebook:")
        for e in eintraege:
            print(f"  {e['notebook']:<24} {e['titel'][:70]}")
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nur-benennen", action="store_true",
                   help="Notebooks nicht ausführen, nur aus dem Manifest zuordnen")
    p.add_argument("--notebook", action="append", metavar="DATEI",
                   help="nur dieses Notebook ausführen (mehrfach angebbar); "
                        "die Manifest-Einträge der übrigen bleiben erhalten")
    p.add_argument("--aufraeumen", action="store_true",
                   help="nach der Zuordnung die Rohdateien in diagramme/ "
                        "löschen — es bleiben nur die benannten Grafiken")
    args = p.parse_args()

    if not args.nur_benennen:
        ausfuehren(nur=args.notebook)
    print("\n--- Zuordnung ---")
    return benennen(aufraeumen=args.aufraeumen)


if __name__ == "__main__":
    sys.exit(main())
