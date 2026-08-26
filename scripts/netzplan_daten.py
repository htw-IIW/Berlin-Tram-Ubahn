#!/usr/bin/env python3
"""Schreibt die Netzgeometrie für die Animation `video/animationen/netzplan.html`.

    python3 scripts/netzplan_daten.py

Erzeugt `video/animationen/netzplan.json` mit drei Teilen:

    linien    je Linie ein oder mehrere Streckenzüge als Liste von [lat, lon]
    paare     die gemeinsamen Standorte beider Netze (Szene 9, „Ortsfaktor")
    meta      Bezugsrahmen, Zeitstempel, Fallzahlen

Nur Tram und U-Bahn — **keine S-Bahn**. Der Netzplan der BVG zeigt alle drei
zusammen; hier geht es um den Vergleich zweier Netze, und eine dritte Farbe im
Bild würde ihn verwässern.

── Woher die Geometrie kommt ─────────────────────────────────────────────────

Die `*-routes`-Indizes sind leer und `stop_sequence` ist nirgends gefüllt
(DATASET.md, Punkt 9). Die Reihenfolge der Halte entlang einer Linie steht also
nirgends fertig da — sie wird hier auf zwei verschiedenen Wegen beschafft:

TRAM — aus den gemessenen Fahrten. Innerhalb einer `trip_id` ergibt die
Sortierung nach `planned_when` die echte Haltefolge. Gezählt werden daraus
nicht ganze Fahrten, sondern **Kantenpaare** (Halt → nächster Halt). Das ist
der entscheidende Punkt: Viele erfasste Fahrten sind unvollständig, weil der
Collector je Haltestelle nur 20 Minuten vorausschaut. Eine halbe Fahrt liefert
aber immer noch lauter richtige Nachbarpaare. Aus den häufigen Kanten wird das
Liniennetz anschließend zusammengesetzt.

U-BAHN — aus der amtlichen Linienfolge (`UBAHN_FOLGEN`, Netzplan der BVG),
Koordinaten aus `ubahn-stops`. Der Messweg scheitert hier an zwei Linien: Die
U1-Fahrten zerfallen im Index in Fragmente von zwei Halten (Median 2), und in
der ausgewerteten Woche taucht **gar keine U4-Fahrt** auf. Beide Linien wären
sonst leer geblieben. Da die Linienfolge einer U-Bahn ohnehin feststeht und
sich im Erhebungszeitraum nicht ändert, ist die amtliche Fassung hier die
verlässlichere Quelle — nicht die bequemere.

── Die Fälle, die man von Hand nachziehen muss ───────────────────────────────

Vier Stationen des U6-Nordastes (Scharnweberstr. bis Alt-Tegel) fehlen in
`ubahn-stops` — das Punktraster der Haltestellensuche reicht nicht bis Tegel.
Ohne sie endet die U6 mitten in Reinickendorf. Sie stehen deshalb mit
Koordinaten aus dem Netzplan in `ERGAENZTE_STATIONEN`; sie sind die einzigen
Punkte der Grafik, die nicht aus der Erhebung stammen.

── Fallstricke ───────────────────────────────────────────────────────────────

1. HALTESTELLENNAMEN SIND NICHT EINDEUTIG. Derselbe Ort erscheint als
   `X (Berlin)`, `X [Tram]`, `X` — je Bahnsteig eine eigene `stop_id`. `basis()`
   schneidet Klammerzusätze ab und mittelt die Koordinaten, sonst zickzackt
   die Linie zwischen den Bahnsteigen derselben Kreuzung.

2. BETRIEBSHALTE FLIEGEN RAUS (`ist_betriebliche_haltestelle`). Betriebshöfe
   und Kehren liegen abseits der Strecke und ziehen sonst lange Zacken ins Netz.

3. SCHWACHE KANTEN FLIEGEN RAUS. Behalten wird nur, was mindestens 15 % der
   häufigsten Kante derselben Linie erreicht. Damit verschwinden Umleitungen
   und die Sprünge, die entstehen, wenn in einer Fahrt ein Halt fehlt.
   Zusätzlich fällt jede Kante über 3,5 km — so weit liegen im Tramnetz keine
   zwei benachbarten Halte auseinander.

4. EINE LINIE KANN MEHRERE ZÜGE HABEN. Äste und Linienvarianten ergeben mehr
   als einen Streckenzug; die Animation zeichnet sie alle. Die Zahl in der
   Ausgabe („2 Züge") ist also kein Fehler.

5. DIE 24 PAARE HÄNGEN AM SCHWELLENWERT. Sie kommen aus `gepaarte_standorte()`
   mit dem Fenster ]−120 s, +240 s[ und mindestens 1.000 Abfahrten je Halt —
   dieselbe Auswahl wie `netzvergleich_gepaart_frueh120.html`. Ändert sich dort
   etwas, ändert sich die Zahl im Sprechtext mit. Sie wird deshalb bei jedem
   Lauf ausgegeben, nicht angenommen.
"""

from __future__ import annotations

import collections
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from elasticsearch import Elasticsearch, helpers                # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER       # noqa: E402
from src.analysis.grafiken import FARBE_NETZ                    # noqa: E402
from src.analysis.karten import anteile_je_haltestelle          # noqa: E402
from src.analysis.quality import ist_betriebliche_haltestelle   # noqa: E402

ZIEL = WURZEL / "video" / "animationen" / "netzplan.json"
# Nur eine Animation. Die Verfrühung stand am 21.08.2026 kurz in einer eigenen
# Datei und ist jetzt die dritte Stufe von netzplan.html — gleiche Bühne,
# gleiche Karte, nur der Satz unten links wechselt.
ANIMATIONEN = (
    WURZEL / "video" / "animationen" / "netzplan.html",
    WURZEL / "video" / "animationen" / "vorspann.html",
)

# Zwischen diesen Marken steht in der Animation die eingebettete Geometrie.
MARKE_AUF = "/* DATEN-ANFANG"
MARKE_ZU = "/* DATEN-ENDE */"

# Eine gewöhnliche Woche im Analysefenster. Mehr bringt nichts: Die Geometrie
# einer Linie ändert sich nicht, und fünf Werktage liefern je Kante längst
# vierstellige Fallzahlen.
FAHRPLANWOCHE = ("2026-05-04", "2026-05-08")

KANTEN_ANTEIL = 0.15      # Kante behalten ab … der häufigsten Kante der Linie
KANTEN_MAX_M = 3_500      # längster plausibler Abstand zweier Nachbarhalte
SCHWELLE_FRUEH_S = -120   # Pünktlichkeitsfenster der Szene 9
SCHWELLE_SPAET_S = 240
MIN_ABFAHRTEN = 1_000     # wie karten.MIN_ABFAHRTEN — Halte darunter sind Rauschen

# Vier Stationen des U6-Nordastes, die in `ubahn-stops` fehlen. Koordinaten aus
# dem Netzplan der BVG — die einzigen Punkte der Grafik, die nicht gemessen sind.
ERGAENZTE_STATIONEN = {
    "U Scharnweberstr.": (52.57119, 13.31855),
    "U Otisstr.":        (52.57739, 13.30692),
    "U Holzhauser Str.": (52.58256, 13.29517),
    "U Borsigwerke":     (52.58698, 13.28581),
    "U Alt-Tegel":       (52.58932, 13.28345),
}

# Amtliche Linienfolgen der U-Bahn, Netzplan der BVG. Namen wie in
# `ubahn-stops`; der Zusatz „ (Berlin)" wird beim Nachschlagen ergänzt.
UBAHN_FOLGEN = {
    "U1": ["U Uhlandstr.", "U Kurfürstendamm", "U Wittenbergplatz",
           "U Nollendorfplatz", "U Kurfürstenstr.", "U Gleisdreieck",
           "U Möckernbrücke", "U Hallesches Tor", "U Prinzenstr.",
           "U Kottbusser Tor", "U Görlitzer Bahnhof", "U Schlesisches Tor",
           "S+U Warschauer Str."],
    # „U Mohrenstr." heißt seit 2024 „U Anton-Wilhelm-Amo-Str."; im Index steht
    # der neue Name, im gedruckten Netzplan je nach Auflage noch der alte.
    "U2": ["U Ruhleben", "U Olympia-Stadion", "U Neu-Westend",
           "U Theodor-Heuss-Platz", "U Kaiserdamm", "U Sophie-Charlotte-Platz",
           "U Bismarckstr.", "U Deutsche Oper", "U Ernst-Reuter-Platz",
           "S+U Zoologischer Garten Bhf", "U Wittenbergplatz",
           "U Nollendorfplatz", "U Bülowstr.", "U Gleisdreieck",
           "U Mendelssohn-Bartholdy-Park", "S+U Potsdamer Platz Bhf",
           "U Anton-Wilhelm-Amo-Str.", "U Stadtmitte", "U Hausvogteiplatz",
           "U Spittelmarkt", "U Märkisches Museum", "U Klosterstr.",
           "S+U Alexanderplatz Bhf", "U Rosa-Luxemburg-Platz",
           "U Senefelderplatz", "U Eberswalder Str.",
           "S+U Schönhauser Allee", "U Vinetastr.", "S+U Pankow"],
    "U3": ["U Krumme Lanke", "U Onkel Toms Hütte", "U Oskar-Helene-Heim",
           "U Freie Universität (Thielplatz)", "U Dahlem-Dorf",
           "U Podbielskiallee", "U Breitenbachplatz", "U Rüdesheimer Platz",
           "U Heidelberger Platz", "U Fehrbelliner Platz", "U Hohenzollernplatz",
           "U Spichernstr.", "U Augsburger Str.", "U Wittenbergplatz",
           "U Nollendorfplatz", "U Kurfürstenstr.", "U Gleisdreieck",
           "U Möckernbrücke", "U Hallesches Tor", "U Prinzenstr.",
           "U Kottbusser Tor", "U Görlitzer Bahnhof", "U Schlesisches Tor",
           "S+U Warschauer Str."],
    "U4": ["U Nollendorfplatz", "U Viktoria-Luise-Platz", "U Bayerischer Platz",
           "U Rathaus Schöneberg", "S+U Innsbrucker Platz"],
    "U5": ["S+U Berlin Hauptbahnhof", "U Bundestag", "S+U Brandenburger Tor",
           "U Unter den Linden", "U Museumsinsel", "U Rotes Rathaus",
           "S+U Alexanderplatz Bhf", "U Schillingstr.",
           "U Strausberger Platz", "U Weberwiese", "U Frankfurter Tor",
           "U Samariterstr.", "S+U Frankfurter Allee", "U Magdalenenstr.",
           "S+U Lichtenberg Bhf", "U Friedrichsfelde", "U Tierpark",
           "U Biesdorf-Süd", "U Elsterwerdaer Platz", "S+U Wuhletal",
           "U Kaulsdorf-Nord", "U Kienberg (Gärten der Welt)",
           "U Cottbusser Platz", "U Hellersdorf", "U Louis-Lewin-Str.",
           "U Hönow"],
    "U6": ["U Alt-Tegel", "U Borsigwerke", "U Holzhauser Str.", "U Otisstr.",
           "U Scharnweberstr.", "U Kurt-Schumacher-Platz",
           "U Afrikanische Str.", "U Rehberge", "U Seestr.", "U Leopoldplatz",
           "U Wedding", "U Reinickendorfer Str.", "U Schwartzkopffstr.",
           "U Naturkundemuseum", "U Oranienburger Tor",
           "S+U Friedrichstr. Bhf", "U Unter den Linden", "U Stadtmitte",
           "U Kochstr. (Checkpoint Charlie)", "U Hallesches Tor",
           "U Mehringdamm", "U Platz der Luftbrücke", "U Paradestr.",
           "U Tempelhof", "U Alt-Tempelhof", "U Kaiserin-Augusta-Str.",
           "U Ullsteinstr.", "U Westphalweg", "U Alt-Mariendorf"],
    "U7": ["S+U Rathaus Spandau", "U Altstadt Spandau", "U Zitadelle",
           "U Haselhorst", "U Paulsternstr.", "U Rohrdamm", "U Siemensdamm",
           "U Halemweg", "U Jakob-Kaiser-Platz", "S+U Jungfernheide Bhf",
           "U Mierendorffplatz", "U Richard-Wagner-Platz", "U Bismarckstr.",
           "U Wilmersdorfer Str.", "U Adenauerplatz", "U Konstanzer Str.",
           "U Fehrbelliner Platz", "U Blissestr.", "U Berliner Str.",
           "U Bayerischer Platz", "U Eisenacher Str.", "U Kleistpark",
           "U Yorckstr.", "U Möckernbrücke", "U Mehringdamm",
           "U Gneisenaustr.", "U Südstern", "U Hermannplatz",
           "U Rathaus Neukölln", "U Karl-Marx-Str.", "U Neukölln",
           "U Grenzallee", "U Blaschkoallee", "U Parchimer Allee",
           "U Britz-Süd", "U Johannisthaler Chaussee", "U Lipschitzallee",
           "U Wutzkyallee", "U Zwickauer Damm", "U Rudow"],
    "U8": ["S+U Wittenau", "S+U Karl-Bonhoeffer-Nervenklinik",
           "U Rathaus Reinickendorf", "U Paracelsus-Bad", "U Lindauer Allee",
           "U Residenzstr.", "U Franz-Neumann-Platz", "U Osloer Str.",
           "U Pankstr.", "S+U Gesundbrunnen Bhf", "U Voltastr.",
           "U Bernauer Str.", "U Rosenthaler Platz", "U Weinmeisterstr.",
           "S+U Alexanderplatz Bhf", "U Jannowitzbrücke",
           "U Heinrich-Heine-Str.", "U Moritzplatz", "U Kottbusser Tor",
           "U Schönleinstr.", "U Hermannplatz", "U Boddinstr.",
           "U Leinestr.", "S+U Hermannstr."],
    "U9": ["U Osloer Str.", "U Nauener Platz", "U Leopoldplatz",
           "U Amrumer Str.", "S+U Westhafen", "U Birkenstr.", "U Turmstr.",
           "U Hansaplatz", "S+U Zoologischer Garten Bhf", "U Kurfürstendamm",
           "U Spichernstr.", "U Güntzelstr.", "U Berliner Str.",
           "U Bundesplatz", "U Friedrich-Wilhelm-Platz",
           "U Walther-Schreiber-Platz", "U Schloßstr.", "S+U Rathaus Steglitz"],
}


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def basis(name: str) -> str:
    """Bahnsteigzusätze abschneiden — `X (Berlin) [Tram]` wird zu `X`.

    ── Warum hier Leerzeichen normalisiert werden ───────────────────────────

    Ein Halt steht im Index unter ZWEI Schreibweisen, die sich nur um ein
    Leerzeichen unterscheiden:

        `Landsberger Allee/ Petersburger Str. (Berlin)`   47.434 Abfahrten
        `Landsberger Allee/Petersburger Str. (Berlin)`

    Ohne diese Normalisierung werden daraus zwei Knoten an derselben Kreuzung.
    Die Kanten der Linie verteilen sich dann auf beide, keine erreicht mehr die
    Kantenschwelle, und **die Linie reißt genau dort auseinander** — sichtbar
    als Lücke im Netz an der Landsberger Allee, bei M5, M6, M8 und M10.

    Der Fehler ist heimtückisch, weil das Netz auch mit der Lücke plausibel
    aussieht: Es fehlt kein ganzer Ast, nur ein Stück Strecke.
    """
    n = re.sub(r"\s*/\s*", "/", name.split("[")[0].replace("(Berlin)", ""))
    return re.sub(r"\s+", " ", n).strip().rstrip(",").strip()


def meter(a, b) -> float:
    """Abstand zweier (lat, lon) in Metern, für Berlin genau genug."""
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


# ── Tram: Geometrie aus den gemessenen Fahrten ───────────────────────────────

def tramkanten(es) -> tuple[dict, dict]:
    """Zählt Nachbarpaare je Tramlinie und mittelt die Koordinaten je Halt."""
    frage = {"query": {"bool": {
        "must": [{"range": {"planned_when": {"gte": FAHRPLANWOCHE[0],
                                             "lt":  FAHRPLANWOCHE[1]}}}],
        "must_not": [{"terms": {"line_name": ["88"]}}],   # SRS, siehe DATASET.md
    }}}
    fahrten: dict[str, dict[str, tuple]] = collections.defaultdict(dict)
    for treffer in helpers.scan(
            es, index="tram-departures-v2", query=frage, size=5_000,
            _source=["trip_id", "line_name", "stop_name", "stop_location",
                     "planned_when"]):
        q = treffer["_source"]
        ort = q.get("stop_location")
        if not ort or not q.get("trip_id"):
            continue
        if ist_betriebliche_haltestelle(q["stop_name"]):
            continue
        fahrten[q["trip_id"]][q["planned_when"]] = (
            q["line_name"], basis(q["stop_name"]), ort["lat"], ort["lon"])

    kanten: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    orte: dict[str, list] = collections.defaultdict(list)
    for halte in fahrten.values():
        folge = [v for _, v in sorted(halte.items())]
        if not folge:
            continue
        linie, kette = folge[0][0], []
        for _, name, lat, lon in folge:
            orte[name].append((lat, lon))
            if not kette or kette[-1] != name:
                kette.append(name)
        for a, b in zip(kette, kette[1:]):
            kanten[linie][tuple(sorted((a, b)))] += 1

    mitte = {name: (round(sum(x for x, _ in p) / len(p), 5),
                    round(sum(y for _, y in p) / len(p), 5))
             for name, p in orte.items()}
    print(f"  {len(fahrten):,} Fahrten, {len(mitte)} Halte, "
          f"{len(kanten)} Linien".replace(",", "."))
    return kanten, mitte


def zuege(kanten: collections.Counter, mitte: dict) -> list[list[str]]:
    """Setzt aus den starken Kanten einer Linie Streckenzüge zusammen.

    Gelaufen wird von einem freien Ende aus; an Verzweigungen gewinnt die
    geradeste Fortsetzung. Ohne diese Regel biegt der Weg an Kreuzungen in den
    Ast ab und lässt den Hauptstrang als Stummel zurück.
    """
    grenze = max(kanten.values()) * KANTEN_ANTEIL
    offen = {k for k, n in kanten.items()
             if n >= grenze and meter(mitte[k[0]], mitte[k[1]]) < KANTEN_MAX_M}
    if len(offen) < 3:
        return []

    nachbarn: dict[str, set] = collections.defaultdict(set)
    for a, b in offen:
        nachbarn[a].add(b)
        nachbarn[b].add(a)

    def weiter(weg: list[str]) -> list[str]:
        while True:
            frei = [n for n in nachbarn[weg[-1]]
                    if tuple(sorted((weg[-1], n))) in offen]
            if not frei:
                return weg
            if len(weg) > 1:
                v = (mitte[weg[-1]][0] - mitte[weg[-2]][0],
                     mitte[weg[-1]][1] - mitte[weg[-2]][1])

                def knick(n: str) -> float:
                    w = (mitte[n][0] - mitte[weg[-1]][0],
                         mitte[n][1] - mitte[weg[-1]][1])
                    norm = math.hypot(*v) * math.hypot(*w) or 1.0
                    return -(v[0] * w[0] + v[1] * w[1]) / norm

                frei.sort(key=knick)
            offen.discard(tuple(sorted((weg[-1], frei[0]))))
            weg.append(frei[0])

    fertig = []
    while offen:
        enden = [k for k in nachbarn
                 if len([n for n in nachbarn[k]
                         if tuple(sorted((k, n))) in offen]) == 1]
        start = enden[0] if enden else next(iter(offen))[0]
        weg = weiter([start])
        if len(weg) > 1:
            fertig.append(weg)
    return verbinden(sorted(fertig, key=len, reverse=True), mitte)


def verbinden(wege: list[list[str]], mitte: dict,
              hoechstabstand_m: float = 2_500) -> list[list[str]]:
    """Haengt Bruchstuecke derselben Linie an ihren naechsten Enden zusammen.

    ── Warum das noetig ist ────────────────────────────────────────────────

    Der Lauf durch die starken Kanten endet an jeder Verzweigung. Eine Linie
    zerfaellt dadurch in mehrere Stuecke, und das Netz bekommt sichtbare
    Loecher — an der Landsberger Allee war eines davon so gross, dass die
    Linie dort schlicht unterbrochen aussah.

    Hier werden die Stuecke wieder aneinandergesetzt: Es wird immer das Paar
    von Enden gesucht, das am dichtesten beieinander liegt, und die beiden
    Stuecke werden dort verbunden. Ueber `hoechstabstand_m` hinaus wird nicht
    verbunden — was so weit auseinanderliegt, ist ein echter Ast und keine
    Luecke, und eine Linie quer durch die Stadt zu ziehen waere schlimmer als
    das Loch.
    """
    wege = [list(w) for w in wege]
    while len(wege) > 1:
        bestes = None
        for i in range(len(wege)):
            for j in range(i + 1, len(wege)):
                # Beide Stuecke lassen sich an je zwei Enden anschliessen.
                for a_um in (False, True):
                    for b_um in (False, True):
                        a = wege[i][::-1] if a_um else wege[i]
                        b = wege[j][::-1] if b_um else wege[j]
                        d = meter(mitte[a[-1]], mitte[b[0]])
                        if bestes is None or d < bestes[0]:
                            bestes = (d, i, j, a_um, b_um)
        d, i, j, a_um, b_um = bestes
        if d > hoechstabstand_m:
            break
        a = wege[i][::-1] if a_um else wege[i]
        b = wege[j][::-1] if b_um else wege[j]
        # Der Anschlusshalt darf nicht doppelt in der Linie stehen.
        wege[i] = a + (b[1:] if b[0] == a[-1] else b)
        wege.pop(j)
    return wege


# ── U-Bahn: amtliche Linienfolge, Koordinaten aus dem Index ──────────────────

def bahnhofskern(name: str) -> str:
    """Reduziert einen Haltestellennamen auf den Bahnhof, den er meint.

        `S+U Alexanderplatz Bhf/Gontardstr. (Berlin)` → `Alexanderplatz`
        `U Naturkundemuseum (Berlin) [Invalidenstr.]` → `Naturkundemuseum`

    Damit fallen die vier Alexanderplatz-Bahnsteige der Tram auf denselben
    Schlüssel wie die U-Bahn-Station.
    """
    n = re.sub(r"\[.*?\]", "", name).replace("(Berlin)", "").strip()
    n = re.sub(r"^(S\+U|U)\s+", "", n).split("/")[0].strip().rstrip(",")
    return re.sub(r"\s+Bhf$", "", n).strip()


def gemeinsame_orte(tram, ubahn):
    """Orte, an denen beide Netze halten — erkannt am NAMEN, nicht am Abstand.

    ── Warum nicht über den Abstand ─────────────────────────────────────────

    `karten.gepaarte_standorte()` nimmt zu jeder U-Bahn-Station den nächsten
    Tramhalt im Umkreis von 300 m. Das erzeugt drei Paare, die keine sind:

        U Unter den Linden  ← Universitätsstr.            292 m
        U Turmstr.          ← Lübecker Str.               279 m
        U Rotes Rathaus     ← Spandauer Str./Marienkirche 231 m

    Das sind Nachbarhaltestellen, keine Umsteigepunkte. An U Turmstr. fährt
    im Erhebungszeitraum gar keine Tram — die M10 endet an Lübecker Str., eine
    Station davor. Wer diese drei mitzählt, vergleicht wieder zwei Orte statt
    einen, und genau das soll die Auswahl ja ausschließen.

    Der Abstand hat noch einen zweiten Fehler: Er nimmt je Station **einen**
    Tramhalt. Am Alexanderplatz war das der Bahnsteig Dircksenstr. mit 16.550
    Abfahrten — die Bahnsteige Gontardstr. (81.083) und Memhardstr. (34.567)
    fielen unter den Tisch, obwohl sie derselbe Ort sind.

    ── Die Regel hier ───────────────────────────────────────────────────────

    Die BVG benennt den Tramhalt am Umsteigepunkt nach der U-Bahn-Station:
    `U Eberswalder Str.`, `S+U Pankow`, `U Tierpark`. Gezählt wird deshalb ein
    Ort genau dann, wenn ein Tramhalt das Präfix `U ` oder `S+U ` trägt und
    sein Bahnhofskern zu einer U-Bahn-Station passt. Alle passenden Bahnsteige
    gehen mengengewichtet in die Tramseite ein.

    Das Verfahren ist strenger als der Umkreis und braucht keinen frei
    gewählten Radius. Es findet 21 Orte statt 24.
    """
    t = tram[tram["count"] >= MIN_ABFAHRTEN]
    u = ubahn[ubahn["count"] >= MIN_ABFAHRTEN]
    stationen = {bahnhofskern(r.stop_name): r for r in u.itertuples()}

    gruppen: dict[str, list] = {}
    for halt in t.itertuples():
        if not re.match(r"^(S\+U|U)\s+", halt.stop_name):
            continue
        kern = bahnhofskern(halt.stop_name)
        if kern in stationen:
            gruppen.setdefault(kern, []).append(halt)

    orte = []
    for kern, halte in gruppen.items():
        station = stationen[kern]
        n = sum(h.count for h in halte)

        def mengengewichtet(feld: str) -> float:
            return sum(getattr(h, feld) * h.count for h in halte) / n

        tram_pct = mengengewichtet("anteil_ausserhalb")
        tram_frueh = mengengewichtet("anteil_frueh")
        tram_spaet = mengengewichtet("anteil_spaet")
        orte.append({
            "ort": kern,
            "station": station.stop_name,
            "tramhalte": [h.stop_name for h in halte],
            # Gezeichnet wird die Station; die Trambahnsteige liegen um sie herum.
            "lat": round(float(station.lat), 5),
            "lon": round(float(station.lon), 5),
            "tram_pct": round(float(tram_pct), 1),
            "ubahn_pct": round(float(station.anteil_ausserhalb), 1),
            "differenz_pp": round(float(tram_pct - station.anteil_ausserhalb), 1),
            "tram_frueh": round(float(tram_frueh), 1),
            "tram_spaet": round(float(tram_spaet), 1),
            "ubahn_frueh": round(float(station.anteil_frueh), 1),
            "ubahn_spaet": round(float(station.anteil_spaet), 1),
            # ── Womit „überwiegend zu früh" gemeint ist ──────────────────────
            # Verglichen wird die Tram MIT SICH SELBST: Fährt sie an diesem
            # Halt öfter zu früh als zu spät? Das ist die Frage der Animation
            # („wo fährt die Tram zu früh ab") und ergibt 14 von 21.
            #
            # Nicht zu verwechseln mit der Frage, woraus ihr RÜCKSTAND auf die
            # U-Bahn besteht (Δfrüh gegen Δspät) — die ergibt 16 von 21. Beide
            # Zahlen sind richtig, sie beantworten Verschiedenes. Im Bild steht
            # die erste, in der Unterzeile der Anteil am Rückstand.
            "ueberwiegend": "frueh" if tram_frueh > tram_spaet else "spaet",
            "tram_n": int(n),
            "ubahn_n": int(station.count),
            "abstand_m": round(min(
                meter((station.lat, station.lon), (h.lat, h.lon)) for h in halte)),
        })
    return sorted(orte, key=lambda o: -o["differenz_pp"])


def ohne_praefix(name: str) -> str:
    """`S+U Wedding` und `U Wedding` sind derselbe Bahnhof — Präfix abschneiden.

    Ob eine Station im Index mit `U ` oder mit `S+U ` geführt wird, hängt daran,
    ob dort auch eine S-Bahn hält — im Netzplan steht dann mal das eine, mal das
    andere. Über den blanken Namen zu suchen, erspart es, sieben Sonderfälle
    (Wedding, Tempelhof, Yorckstr., Neukölln, Jannowitzbrücke, Bundesplatz,
    Heidelberger Platz) von Hand nachzupflegen.
    """
    for p in ("S+U ", "U "):
        if name.startswith(p):
            return name[len(p):]
    return name


def ubahnorte(es) -> dict:
    """Alle U-Bahn-Stationen mit Koordinate, Schlüssel ohne Präfix und Zusatz."""
    orte: dict[str, list] = collections.defaultdict(list)
    for treffer in helpers.scan(es, index="ubahn-stops",
                                query={"query": {"match_all": {}}}):
        q = treffer["_source"]
        orte[ohne_praefix(basis(q["name"]))].append(
            (q["location"]["lat"], q["location"]["lon"]))
    # U Stadtmitte liegt zweimal im Index — die Bahnsteige von U2 und U6
    # kreuzen sich, sie liegen 200 m auseinander. Der Mittelpunkt genügt.
    mitte = {n: (round(sum(x for x, _ in p) / len(p), 5),
                 round(sum(y for _, y in p) / len(p), 5))
             for n, p in orte.items()}
    mitte.update({ohne_praefix(n): (round(lat, 5), round(lon, 5))
                  for n, (lat, lon) in ERGAENZTE_STATIONEN.items()
                  if ohne_praefix(n) not in mitte})
    return mitte


# ── Hauptlauf ────────────────────────────────────────────────────────────────

def main() -> int:
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=900)

    print(f"Tram — Fahrten {FAHRPLANWOCHE[0]} bis {FAHRPLANWOCHE[1]}:")
    kanten, tram_mitte = tramkanten(es)

    linien = []
    for linie in sorted(kanten, key=lambda l: (len(l), l)):
        wege = zuege(kanten[linie], tram_mitte)
        if not wege:
            print(f"  ! {linie}: zu wenig starke Kanten, ausgelassen")
            continue
        linien.append({
            "linie": linie, "netz": "Tram",
            "zuege": [[list(tram_mitte[h]) for h in w] for w in wege],
            "halte": sorted({h for w in wege for h in w}),
        })
        print(f"  {linie:>4}  {len(linien[-1]['halte']):>3} Halte, "
              f"{len(wege)} Zug/Züge")

    print("\nU-Bahn — amtliche Linienfolge:")
    orte = ubahnorte(es)
    for linie, folge in UBAHN_FOLGEN.items():
        fehlt = [n for n in folge if ohne_praefix(n) not in orte]
        if fehlt:
            print(f"  ! {linie}: ohne Koordinate — {', '.join(fehlt)}")
        weg = [n for n in folge if ohne_praefix(n) in orte]
        linien.append({
            "linie": linie, "netz": "U-Bahn",
            "zuege": [[list(orte[ohne_praefix(n)]) for n in weg]],
            "halte": weg,
        })
        print(f"  {linie:>4}  {len(weg):>3} Stationen")

    print("\nGemeinsame Standorte beider Netze:")
    tram = anteile_je_haltestelle(es, "tram-departures-v2",
                                  SCHWELLE_FRUEH_S, SCHWELLE_SPAET_S)
    ubahn = anteile_je_haltestelle(es, "ubahn-departures-v2",
                                   SCHWELLE_FRUEH_S, SCHWELLE_SPAET_S)
    orte = gemeinsame_orte(tram, ubahn)
    schlechter = sum(1 for o in orte if o["differenz_pp"] > 0)
    print(f"  {len(orte)} Orte mit gleichnamigem Tramhalt, "
          f"an {schlechter} davon ist die Tram unpünktlicher")
    for o in orte:
        print(f"    {o['ort']:<26}{o['tram_pct']:>6.1f} %{o['ubahn_pct']:>8.1f} %"
              f"{o['differenz_pp']:>+8.1f} pp   {o['abstand_m']:>3} m"
              f"   {len(o['tramhalte'])} Tramhalt(e)")

    daten = {
        "meta": {
            "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fahrplanwoche": list(FAHRPLANWOCHE),
            "fenster_s": [SCHWELLE_FRUEH_S, SCHWELLE_SPAET_S],
            "farben": FARBE_NETZ,
            "n_paare": len(orte),
            "n_tram_schlechter": schlechter,
            "n_frueh": sum(1 for o in orte if o["ueberwiegend"] == "frueh"),
            "n_spaet": sum(1 for o in orte if o["ueberwiegend"] == "spaet"),
            # Der mittlere Rueckstand und seine zwei Anteile. Die Summe der
            # beiden ergibt den Rueckstand — das ist die Aussage der Szene:
            # rund zwei Drittel davon sind Verfruehung, nicht Verspaetung.
            "rueckstand_pp": round(
                sum(o["differenz_pp"] for o in orte) / len(orte), 1),
            "rueckstand_frueh_pp": round(sum(
                o["tram_frueh"] - o["ubahn_frueh"] for o in orte) / len(orte), 1),
            "rueckstand_spaet_pp": round(sum(
                o["tram_spaet"] - o["ubahn_spaet"] for o in orte) / len(orte), 1),
            "ergaenzte_stationen": sorted(ERGAENZTE_STATIONEN),
        },
        "linien": linien,
        "paare": orte,
    }

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"\ngeschrieben: {ZIEL.relative_to(WURZEL)}")

    for pfad in ANIMATIONEN:
        if einbetten(daten, pfad):
            print(f"eingetragen: {pfad.relative_to(WURZEL)}")
    return 0


def einbetten(daten: dict, ziel: Path) -> bool:
    """Trägt die Geometrie in die Animation ein, zwischen die zwei Marken.

    Die Animation muss ohne Server laufen — im Schnittprogramm wird sie als
    Datei geöffnet, und ein `fetch()` auf die Nachbardatei scheitert dort an
    der Herkunftsregel des Browsers. Die Daten stehen deshalb im HTML. Damit
    sie trotzdem erzeugt bleiben und nicht von Hand gepflegt werden, schreibt
    dieses Skript sie bei jedem Lauf neu hinein.
    """
    if not ziel.exists():
        print(f"  (noch keine {ziel.name} — übersprungen)")
        return False

    text = ziel.read_text(encoding="utf-8")
    auf, zu = text.find(MARKE_AUF), text.find(MARKE_ZU)
    if auf < 0 or zu < auf:
        raise SystemExit(f"{ziel.name}: Marken {MARKE_AUF} … {MARKE_ZU} "
                         "nicht gefunden — wurde der Datenblock entfernt?")

    block = (f"{MARKE_AUF} — erzeugt von scripts/{Path(__file__).name}, "
             "nicht von Hand ändern */\n"
             "      const DATEN = "
             + json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
             + ";\n      ")
    ziel.write_text(text[:auf] + block + text[zu:], encoding="utf-8")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
