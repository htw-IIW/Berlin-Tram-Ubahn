# src/analysis/karten.py
# Gemeinsame Bausteine der Folium-Karten aus notebooks/03_lsa_analyse.ipynb.
#
# ── Warum dieses Modul existiert ─────────────────────────────────────────────
#
# Die Legende ist fuer die Videoaufnahme gebaut: gross, kontrastreich, mit der
# Maus verschiebbar, per Taste L ausblendbar. Das sind rund hundert Zeilen CSS
# und JavaScript. Sie standen bisher vollstaendig in der Zelle der ersten Karte.
#
# Die zweite Karte hat den Block nur teilweise kopiert — die Klassennamen ja,
# das <style> und das <script> nicht. Da jede Karte eine eigene HTML-Datei ist,
# hatte die zweite Legende deshalb **keinerlei Formatierung**: nicht positioniert,
# nicht verschiebbar, unlesbar. Der Fehler war unsichtbar, solange man nur die
# erste Karte ansah.
#
# Seit dem Umbau vom 09.08.2026 gibt es drei Karten. Ein drittes Mal kopieren
# haette den Fehler ein drittes Mal riskiert; deshalb steht der Baustein hier.
#
# ── Farben ───────────────────────────────────────────────────────────────────
#
# Die Karten benutzen bewusst NICHT das Netzpaar Rot/Blau aus
# src/analysis/grafiken.py. Dort heisst Rot "Tram" und Blau "U-Bahn". Im Video
# laeuft unmittelbar vor der ersten Karte das Balkendiagramm mit genau dieser
# Zuordnung — blaue Punkte auf einer Berliner Karte waeren dann als
# U-Bahn-Stationen lesbar, und die Karte zeigt ausschliesslich Tramhalte.
#
# Gewaehlt ist deshalb ein eigenes divergierendes Paar, geprueft mit dem
# Validator der dataviz-Vorlage gegen helle Flaeche:
#
#     Lila #7B1FA2 gegen Orange #E65100
#     Helligkeit, Chroma und Kontrast bestanden,
#     Abstand unter Protanopie 28,7 — unter Tritanopie 26,2 (Grenze 8)
#
# Bis zum 26.08.2026 stand hier Tuerkis #0097A7 statt Lila; die Umstellung war
# eine Gestaltungsentscheidung der Nutzerin. Das neue Paar ist unter Protanopie
# klar besser trennbar als das alte (28,7 gegen 19,0), unter Tritanopie etwas
# schwaecher (26,2 gegen 35,2) — beides weit ueber der Grenze.
#
# Die Bedeutung ist auf beiden Karten dieselbe und darf nicht getauscht werden:
#
#     LILA   = die harmlosere Richtung im Bild (zu frueh / baut Verspaetung ab)
#     ORANGE = die Richtung, um die es in der Handlungsempfehlung geht
#              (zu spaet / erzeugt Verspaetung)

FARBE_FRUEH = "#7B1FA2"   # lila    — ueberwiegend zu frueh / baut Verspaetung ab
FARBE_SPAET = "#E65100"   # orange  — ueberwiegend zu spaet / erzeugt Verspaetung
FARBE_NEUTRAL = "#B0BEC5"  # grau    — Mittelpunkt der divergierenden Skala

# Farben der LSA-Zuordnung. Unveraendert aus der bisherigen Kartenzelle
# uebernommen, damit die eingefaerbte Fassung wie gehabt aussieht.
FARBE_LSA = {
    "aktiv":    "#43A047",
    "inaktiv":  "#E53935",
    "kein_lsa": "#9E9E9E",
}


# ── Grundkarte ───────────────────────────────────────────────────────────────
#
# Bis zum 26.08.2026 lagen alle Karten auf "CartoDB positron". CARTO hat den
# Rasterdienst basemaps.cartocdn.com inzwischen schluesselpflichtig gemacht und
# kuendigt ihn ab: Anfragen ohne API-Key bekommen die Kacheln mit einem
# diagonalen Wasserzeichen "API KEY REQUIRED" quer ueber die Stadt. Der Fehler
# war im Code nicht zu sehen — die Karten funktionierten weiter, nur die
# fertigen HTML-Dateien waren fuer die Aufnahme unbrauchbar.
#
# Ersatz ist Esris "World Light Gray Canvas": dieselbe zurueckhaltende helle
# Optik, kein Schluessel, kein Kontingent. Er kommt allerdings in zwei Ebenen,
# Flaeche und Beschriftung getrennt. Positron hatte beides in einer Kachel;
# ohne die zweite Ebene stuende die Karte ohne Stadtteilnamen da, und im Video
# orientiert sich das Publikum genau daran ("Mitte", "Kreuzberg").
#
# Die Alternative waere ein CARTO-Schluessel gewesen (kostenlos, 5 Mio. Kacheln
# im Monat). Dagegen sprach, dass er in einem oeffentlichen Repo aus .env
# kommen muesste und dass der Dienst ohnehin auslaeuft.

KACHELN_URL = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
               "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}")
KACHELN_SCHRIFT_URL = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
                       "Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}")
KACHELN_QUELLE = ("Kartengrundlage: Esri, HERE, Garmin, "
                  "© OpenStreetMap-Mitwirkende")

# Der Dienst hat Kacheln bis Zoomstufe 16. Ohne diese Grenze laesst Leaflet
# weiter hineinzoomen und zeigt dann eine leere Flaeche.
KACHELN_MAX_ZOOM = 16


def grundkarte(**kwargs):
    """Folium-Karte auf der hellgrauen Esri-Grundkarte, Beschriftung obenauf.

    `kwargs` gehen unveraendert an folium.Map (location, zoom_start, ...).

    Beide Kachelebenen sind mit control=False eingehaengt: In der Ebenenauswahl
    neben der Legende sollen nur die inhaltlichen Gruppen stehen, nicht die
    Grundkarte. Frueher tauchte dort "cartodbpositron" auf.
    """
    import folium

    kwargs.setdefault("max_zoom", KACHELN_MAX_ZOOM)
    karte = folium.Map(tiles=None, **kwargs)
    folium.TileLayer(KACHELN_URL, attr=KACHELN_QUELLE, name="Grundkarte",
                     control=False, max_zoom=KACHELN_MAX_ZOOM).add_to(karte)
    folium.TileLayer(KACHELN_SCHRIFT_URL, attr=KACHELN_QUELLE,
                     name="Beschriftung", overlay=True, control=False,
                     max_zoom=KACHELN_MAX_ZOOM).add_to(karte)
    return karte


def _mische(hex_farbe: str, anteil: float) -> str:
    """Blendet `hex_farbe` mit `anteil` (0..1) gegen FARBE_NEUTRAL.

    anteil = 0 ergibt reines Grau, anteil = 1 die volle Farbe. Damit bekommt
    eine divergierende Skala einen echten neutralen Mittelpunkt, statt bei
    schwachen Werten schon farbig zu werden.
    """
    def zerlegen(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    ziel = zerlegen(hex_farbe)
    grund = zerlegen(FARBE_NEUTRAL)
    anteil = max(0.0, min(1.0, anteil))
    kanal = [round(g + (z - g) * anteil) for g, z in zip(grund, ziel)]
    return "#{:02x}{:02x}{:02x}".format(*kanal)


def divergierende_farbe(wert: float, spanne: float) -> str:
    """Tuerkis fuer negative, Orange fuer positive Werte, Grau bei null.

    `spanne` ist der Betrag, ab dem die Farbe voll gesaettigt ist — ueblich das
    95. Perzentil, damit einzelne Ausreisser nicht die ganze Skala verbrauchen.
    """
    if not spanne:
        return FARBE_NEUTRAL
    anteil = min(abs(wert) / spanne, 1.0)
    return _mische(FARBE_SPAET if wert >= 0 else FARBE_FRUEH, anteil)


def radius_aus_anteil(wert: float, hoechstwert: float,
                      r_min: float = 4.0, r_max: float = 20.0) -> float:
    """Kreisradius linear zwischen r_min und r_max.

    Bewusst linear und nicht flaechenproportional: Auf der Karte werden die
    Kreise nicht gegeneinander gemessen, sondern als "gross" oder "klein"
    gelesen. Die Legende schreibt die Zuordnung ohnehin aus.

    Wird noch von der Karte der erzeugten Verspaetung benutzt, wo der Wert eine
    stetige Sekundenzahl ohne natuerliche Stufen ist. Fuer Prozentanteile ist
    STUFEN_ANTEIL die bessere Wahl — siehe dort.
    """
    if not hoechstwert:
        return r_min
    return r_min + (r_max - r_min) * min(max(wert, 0.0) / hoechstwert, 1.0)


# ── Abgestufte Kreisgroessen fuer Prozentanteile ─────────────────────────────
#
# Eine stetige Skala hat auf einer Karte mit mehreren hundert Punkten einen
# praktischen Nachteil: Zwei Halte mit 31 % und 34 % bekommen fast denselben
# Radius, und niemand kann aus einem Kreis den Wert ablesen. Der Betrachter
# liest ohnehin in Klassen — "klein", "mittel", "gross".
#
# Feste Stufen machen daraus eine Aussage, die man auch aussprechen kann:
# "die grossen Kreise sind die Halte mit ueber 20 Prozent". Zusaetzlich haengt
# das Bild damit nicht mehr am 95. Perzentil der gerade geladenen Daten — bei
# laufender Erhebung wanderte die Skala sonst bei jedem Durchlauf.
#
# Stufenweite am 10.08.2026 von 10 auf 5 Prozentpunkte halbiert. Grund: Mit dem
# Vertragsfenster (-120 / +240 statt -120 / +180) reicht die Spanne der Tram nur
# noch von 0,4 % bis 31,5 % statt bis ueber 40 %. Unter der alten Einteilung
# lagen 227 von 396 Halten in einer einzigen Stufe, die oberste blieb leer — die
# Legende versprach eine Klasse, die es nicht gab, und der groesste sichtbare
# Kreis sah dadurch mittelmaessig aus.
#
# Besetzung unter der jetzigen Einteilung:
#
#            < 5 %   5-10   10-15   15-20   > 20 %
#   Tram        34     50     101     126       85
#   U-Bahn     149     20       0       0        0
#
# Die U-Bahn bleibt damit sichtbar am unteren Ende — der Groessenkontrast, der
# die Aussage der Karte traegt, bleibt erhalten und wird sogar etwas feiner.
#
# (Untergrenze in Prozentpunkten, Radius in Pixeln)
STUFEN_ANTEIL = [(0, 5), (5, 9), (10, 13), (15, 18), (20, 24)]


def radius_gestuft(anteil: float, stufen=STUFEN_ANTEIL) -> float:
    """Radius nach der hoechsten Stufe, die `anteil` erreicht."""
    radius = stufen[0][1]
    for grenze, r in stufen:
        if anteil >= grenze:
            radius = r
    return radius


def stufen_legende(stufen=STUFEN_ANTEIL) -> list[tuple[str, str]]:
    """Legendenzeilen zu STUFEN_ANTEIL — Beschriftung aus den Stufen erzeugt,
    damit sie nicht von ihnen abweichen kann."""
    zeilen = []
    for i, (grenze, r) in enumerate(stufen):
        if i + 1 < len(stufen):
            text = (f"unter {stufen[1][0]} %" if i == 0
                    else f"{grenze} bis {stufen[i + 1][0]} %")
        else:
            text = f"{grenze} % und mehr"
        zeilen.append((kreis(int(r * 2)), text))
    return zeilen


# ── Legende ──────────────────────────────────────────────────────────────────
# Das <style> und das <script> stehen genau einmal. Jede Karte bekommt eine
# eigene HTML-Datei, deshalb muss der Block in jede Datei hinein — aber aus
# derselben Quelle.

_STIL_UND_SKRIPT = """
<style>
#lsa-legende {
  position: absolute; top: 24px; right: 24px; z-index: 9999;
  background: rgba(255,255,255,.96); border: 2px solid #37474F;
  border-radius: 10px; padding: 0 0 14px 0; width: 320px;
  font-family: -apple-system, "Segoe UI", Helvetica, sans-serif;
  font-size: 16px; color: #263238; box-shadow: 0 6px 22px rgba(0,0,0,.28);
  user-select: none;
}
#lsa-legende-griff {
  cursor: grab; background: #37474F; color: #fff; font-weight: 600;
  padding: 9px 14px; border-radius: 7px 7px 0 0; font-size: 17px;
}
#lsa-legende-griff span { float: right; font-weight: 400; opacity: .75; font-size: 14px; }
#lsa-legende-griff:active { cursor: grabbing; }
.lsa-block { padding: 12px 14px 4px 14px; }
.lsa-titel { font-weight: 700; margin-bottom: 8px; font-size: 15px;
             text-transform: uppercase; letter-spacing: .04em; color: #546E7A; }
.lsa-zeile { display: flex; align-items: center; gap: 11px; margin-bottom: 9px;
             line-height: 1.25; }
.lsa-punkt { width: 20px; height: 20px; border-radius: 50%; flex: 0 0 auto;
             opacity: .85; border: 1px solid rgba(0,0,0,.28); }
.lsa-kreis { border-radius: 50%; background: #78909C; opacity: .55;
             border: 1px solid rgba(0,0,0,.3); flex: 0 0 auto; }
.lsa-fuss { padding: 6px 14px 0 14px; font-size: 13px; color: #607D8B;
            border-top: 1px solid #ECEFF1; margin-top: 6px; padding-top: 10px;
            line-height: 1.35; }
</style>

<script>
(function () {
  var box = document.getElementById('lsa-legende');
  var griff = document.getElementById('lsa-legende-griff');
  if (!box || !griff) return;
  var aktiv = false, dx = 0, dy = 0;

  // Ohne stopPropagation zieht Leaflet die Karte mit, sobald man die
  // Legende bewegt.
  ['mousedown', 'dblclick', 'wheel'].forEach(function (ev) {
    box.addEventListener(ev, function (e) { e.stopPropagation(); });
  });

  griff.addEventListener('mousedown', function (e) {
    aktiv = true;
    var r = box.getBoundingClientRect();
    dx = e.clientX - r.left; dy = e.clientY - r.top;
    box.style.right = 'auto'; box.style.bottom = 'auto';
    e.preventDefault();
  });
  document.addEventListener('mousemove', function (e) {
    if (!aktiv) return;
    box.style.left = (e.clientX - dx) + 'px';
    box.style.top  = (e.clientY - dy) + 'px';
  });
  document.addEventListener('mouseup', function () { aktiv = false; });

  // L blendet die Legende aus, falls sie beim Zoomen im Weg ist.
  document.addEventListener('keydown', function (e) {
    if (e.key === 'l' || e.key === 'L') {
      box.style.display = (box.style.display === 'none') ? 'block' : 'none';
    }
  });
})();
</script>
"""


def legende(titel: str, bloecke: list[tuple[str, list[tuple[str, str]]]],
            fuss: str) -> str:
    """Baut den HTML-Block der Legende.

    bloecke: Liste von (Ueberschrift, [(Symbol-HTML, Beschriftung), ...]).
    Das Symbol-HTML ist entweder ein farbiger Punkt oder ein grauer Kreis in
    einer bestimmten Groesse — beides erzeugen `punkt()` und `kreis()`.
    """
    teile = [
        '<div id="lsa-legende">',
        f'  <div id="lsa-legende-griff">{titel} &nbsp;<span>⠿ ziehen</span></div>',
    ]
    for ueberschrift, zeilen in bloecke:
        teile.append('  <div class="lsa-block">')
        teile.append(f'    <div class="lsa-titel">{ueberschrift}</div>')
        for symbol, text in zeilen:
            teile.append(f'    <div class="lsa-zeile">{symbol}{text}</div>')
        teile.append("  </div>")
    teile.append(f'  <div class="lsa-fuss">{fuss}</div>')
    teile.append("</div>")
    return "\n".join(teile) + _STIL_UND_SKRIPT


def punkt(farbe: str) -> str:
    return f'<span class="lsa-punkt" style="background:{farbe}"></span>'


def kreis(px: int) -> str:
    return f'<span class="lsa-kreis" style="width:{px}px;height:{px}px"></span>'


# ── Daten und Kartenbau ──────────────────────────────────────────────────────
#
# Steht hier und nicht im Notebook, damit dieselbe Karte fuer beide Netze und
# fuer mehrere Schwellen erzeugt werden kann, ohne sie mehrfach zu schreiben.
# scripts/karten_zuverlaessigkeit.py ist der schnelle Weg (Sekunden statt eines
# Notebook-Laufs), das Notebook ruft dieselben Funktionen auf.

# Mindestzahl Abfahrten, damit ein Halt gezeichnet wird.
#
# Ohne diese Grenze zeichnet die Karte "Altes Wasserwerk" mit sechs erfassten
# Abfahrten und 100 % ausserhalb des Fensters als groessten Kreis im Bild —
# neben Halten mit 27.000 Abfahrten. Ein Anteil ist bei winzigem Nenner
# wertlos. Betroffen sind 3 von 399 Tramhalten.
MIN_ABFAHRTEN = 1_000


def anteile_je_haltestelle(es, index: str, schwelle_frueh_s: int,
                           schwelle_spaet_s: int,
                           max_haltestellen: int = 2000,
                           query: dict | None = None):
    """Je Haltestelle: Anteil zu frueher, zu spaeter und ausserhalb liegender
    Abfahrten, dazu Koordinaten, Mittelwert und Fallzahl.

    Eine einzige Aggregation. Nenner ist ueberall die Zahl der Abfahrten MIT
    Echtzeitwert — die Filter koennen nur solche Dokumente treffen, ein anderer
    Nenner wuerde die Anteile systematisch kleinrechnen.

    ── Drei Sekundenkennzahlen, drei Nullpunkte ─────────────────────────────

    `anteil_spaet` zaehlt nur, DASS eine Abfahrt jenseits der Grenze liegt, und
    `avg_delay_s` misst in Sekunden, verrechnet dafuer aber Verfruehung gegen
    Verspaetung — die Kennzahl, die Szene 4 des Films als irrefuehrend vorfuehrt.
    Dazwischen liegen zwei Kennzahlen, die in Sekunden messen, ohne
    gegenzurechnen. Beide sind `mean(max(delay_s - schwelle, 0))` ueber alle
    Abfahrten mit Echtzeitwert; sie unterscheiden sich nur im Nullpunkt:

        avg_delay_s     Verfruehung zaehlt NEGATIV und zieht den Wert herunter
        verspaetung_s   Nullpunkt Fahrplanzeit — reine Verspaetung, Verfruehung 0
        ueberzug_s      Nullpunkt `schwelle_spaet_s` — nur was der Vertrag
                        ueberhaupt als Verspaetung zaehlt (3½ Minuten)

    Der Unterschied zwischen den ersten beiden isoliert genau den Effekt, den
    Szene 4 vorfuehrt: Was von einem Abstand uebrig bleibt, wenn Verfruehung
    ihn nicht mehr mit erzeugen darf.

    ── `query`: standardmaeszig KEIN Filter ─────────────────────────────────

    Ohne `query` laeuft die Aggregation ueber den GANZEN Index — also
    einschlieszlich Wochenenden, einschlieszlich des Collector-Ausfalls und
    ohne den Analysezeitraum. Fuer die Karten ist das so gewollt und seit
    jeher so: Sie zeigen den Bestand, und ihre Kreise haengen an Anteilen, die
    von der Abtastdichte kaum abhaengen.

    Sobald eine Auswertung neben eine gestellt wird, die tageweise laedt —
    `lade_fahrten()` und `segmente_gesamtzeitraum()` sieben Wochenenden und
    den Ausfall aus —, stimmen die Grundgesamtheiten NICHT mehr ueberein. Dann
    gehoert hier `analysefenster_query()` hinein, bei Bedarf zusammen mit
    `werktagsfilter()`. Beides steht in quality.py.

    Der Unterschied ist nicht klein: Ueber den Tram-Index verschiebt die volle
    Regel den Mittelwert einzelner Halte um mehr als zehn Sekunden und
    veraendert die Rangfolge der obersten zehn.

    Gerechnet ohne Script-Aggregation, aus zwei Filter-Teilaggregationen:
    Summe der Ueberschreitungen = n * (Mittelwert der Gefilterten - Schwelle).
    Das ist exakt und kostet nur zwei weitere Teilaggregationen — eine
    Script-Aggregation ueber 14 Mio. Dokumente kostet auf dem Pi mit 0,5 GB
    Heap deutlich mehr.
    """
    import pandas as pd

    antwort = es.search(
        index=index, size=0,
        **({"query": query} if query else {}),
        aggs={"stops": {
            "terms": {"field": "stop_name", "size": max_haltestellen},
            "aggs": {
                "avg_delay": {"avg": {"field": "delay_s"}},
                "n_delay":   {"value_count": {"field": "delay_s"}},
                "zu_frueh":  {"filter": {"range": {
                    "delay_s": {"lte": schwelle_frueh_s}}}},
                "zu_spaet":  {"filter": {"range": {
                    "delay_s": {"gte": schwelle_spaet_s}}},
                    "aggs": {"avg": {"avg": {"field": "delay_s"}}}},
                "ab_null":   {"filter": {"range": {"delay_s": {"gte": 0}}},
                              "aggs": {"avg": {"avg": {"field": "delay_s"}}}},
                "ort":       {"top_hits": {"size": 1,
                                           "_source": ["stop_location"]}},
            },
        }},
    )

    zeilen = []
    for eimer in antwort["aggregations"]["stops"]["buckets"]:
        treffer = eimer["ort"]["hits"]["hits"]
        if not treffer:
            continue
        ort = treffer[0]["_source"].get("stop_location") or {}
        if ort.get("lat") is None:
            continue
        n = eimer["n_delay"]["value"]
        if not n:
            continue
        k_spaet = eimer["zu_spaet"]["doc_count"]
        frueh = eimer["zu_frueh"]["doc_count"] / n * 100
        spaet = k_spaet / n * 100
        # Kein verspaetetes Dokument heisst kein Ueberzug — der Mittelwert ist
        # dann None, die Summe aber nachweislich null.
        summe_ueberzug = (0.0 if not k_spaet else
                          k_spaet * (eimer["zu_spaet"]["avg"]["value"]
                                     - schwelle_spaet_s))
        k_null = eimer["ab_null"]["doc_count"]
        summe_verspaetung = (0.0 if not k_null else
                             k_null * eimer["ab_null"]["avg"]["value"])
        zeilen.append({
            "stop_name": eimer["key"],
            "lat": ort["lat"], "lon": ort["lon"],
            "avg_delay_s": eimer["avg_delay"]["value"],
            "count": n,
            "anteil_frueh": frueh,
            "anteil_spaet": spaet,
            "verspaetung_s": summe_verspaetung / n,
            "ueberzug_s": summe_ueberzug / n,
            "anteil_ausserhalb": frueh + spaet,
            "uebergewicht": spaet - frueh,
        })
    return pd.DataFrame(zeilen).dropna(subset=["avg_delay_s"])


def _minuten(sekunden: int) -> str:
    """„2 Minuten" statt „120 s".

    Sekundenzahlen gehoeren nicht ins Bild. delay_s ist minutenquantisiert
    (DATASET.md Nr. 1) — eine Sekundenangabe behauptet eine Aufloesung, die die
    Daten nicht haben. Das Raster kennt nur ganze Minuten, also wird auch nur
    in ganzen Minuten beschriftet.
    """
    n = abs(int(sekunden)) // 60
    return f"{n} Minute" if n == 1 else f"{n} Minuten"


def _fussnote_fenster(schwelle_frueh_s: int, schwelle_spaet_s: int) -> str:
    """Schreibt das Fenster aus und ordnet jede Seite gegen den Vertrag ein.

    Die Einordnung gehoert ins Bild, nicht nur in die Dokumentation: Sobald eine
    Zahl von hier neben einer veroeffentlichten BVG-Zahl steht, muss erkennbar
    sein, ob gleich gerechnet wurde.

    ── Die beiden Seiten sind NICHT symmetrisch ────────────────────────────────

    BVG-Verkehrsvertrag seit 01.01.2025: puenktlich ist eine Abfahrt zwischen
    60 s vor und 210 s nach der Sollzeit. delay_s kennt nur Vielfache von 60
    (DATASET.md Nr. 1), und daraus folgt fuer die beiden Seiten Verschiedenes:

    FRUEH — "mehr als 60 s zu frueh" heisst delay_s < -60, im Raster also
    <= -120. Die Stufe -60 ist mehrdeutig: Je nach Rundungskonvention der
    Schnittstelle steht sie fuer 1-60 s oder fuer 31-89 s Verfruehung. -120 ist
    damit die groesste Menge, die die amtliche Bedingung *garantiert* erfuellt.
    Das ist eine getreue, eher zu vorsichtige Umsetzung — wir zaehlen eher zu
    wenige Verfruehungen als zu viele.

    SPAET — "mehr als 210 s" liegt zwischen den Rasterstufen 180 und 240.
    Welche der beiden getreu ist, haengt an der Rundungskonvention:

        rundet die API   Stufe 180 = echte 150-210 s  -> ganz IM Fenster
                         Stufe 240 = echte 210-270 s  -> ganz AUSSERHALB
                         => 240 ist exakt die Vertragsgrenze

        schneidet sie ab Stufe 180 = echte 180-240 s  -> gemischt
                         Stufe 240 = echte 240-299 s  -> zu wenig
                         => 240 unterzaehlt, 180 ueberzaehlt

    Gewaehlt ist 240 (Stand 10.08.2026). Es ist unter der einen Lesart exakt
    und unter der anderen zu vorsichtig — es kann den Abstand zwischen den
    Netzen also nie uebertreiben. 180 waere unter der Rundungslesart schlicht
    falsch: Es zaehlte Fahrten als verspaetet, die im Fenster liegen. Damit
    folgen beide Seiten derselben Regel wie -120 auf der Verfruehungsseite.

    Gegenprobe, damit die Wahl nicht das Ergebnis traegt: Der Abstand zwischen
    den Netzen betraegt bei 180 s das 2,68-fache und bei 240 s das 2,95-fache —
    mit der amtlichen Stufe wird der Unterschied groesser, nicht kleiner.
    """
    zeilen = ["Anteil aller Abfahrten außerhalb des Pünktlichkeitsfensters."]

    if schwelle_frueh_s == -120:
        zeilen.append("<b>zu früh:</b> Verfrühung nach BVG-Verkehrsvertrag — "
                      "mehr als 1 Minute; im Minutenraster der Daten die Stufe "
                      "ab 2 Minuten.")
    else:
        zeilen.append(f"<b>zu früh:</b> ab {_minuten(schwelle_frueh_s)}. Der "
                      "Verkehrsvertrag zählt ab mehr als 1 Minute.")

    if schwelle_spaet_s == 240:
        zeilen.append("<b>zu spät:</b> Verspätung nach BVG-Verkehrsvertrag — "
                      "mehr als 3½ Minuten; im Minutenraster der Daten die "
                      "Stufe ab 4 Minuten.")
    elif schwelle_spaet_s == 180:
        zeilen.append("<b>zu spät:</b> ab 3 Minuten — strenger als der Vertrag, "
                      "der ab 3½ Minuten zählt.")
    else:
        zeilen.append(f"<b>zu spät:</b> ab {_minuten(schwelle_spaet_s)}.")

    return " ".join(zeilen)


# Der Kartentitel heisst NICHT "Zuverlaessigkeit". Im BVG-Verkehrsvertrag ist das
# ein eigener, anders definierter Begriff: Anteil der tatsaechlich erbrachten an
# allen bestellten Fahrten, Zielwert 99,7 % fuer Tram und U-Bahn — also Ausfaelle,
# nicht Puenktlichkeit. Diese Karte zeigt den Anteil ausserhalb des
# PUENKTLICHKEITSfensters. Denselben Fehler hatte das Projekt schon einmal bei
# "Vorrang" gegen "Beeinflussung"; amtliche Begriffe werden hier nicht umgedeutet.
def zuverlaessigkeitskarte(stops, schwelle_frueh_s: int, schwelle_spaet_s: int,
                           titel: str = "Außerhalb des Pünktlichkeitsfensters",
                           min_abfahrten: int = MIN_ABFAHRTEN,
                           zoom: int = 12):
    """Kreisgroesse = Anteil ausserhalb, Farbe = welche Richtung ueberwiegt."""
    import folium

    daten = stops[stops["count"] >= min_abfahrten].copy()
    # Immer neu ableiten statt auf eine mitgelieferte Spalte zu vertrauen: Ein
    # Aufrufer, der die Anteile selbst zusammengestellt hat, brachte sie sonst
    # nicht mit, und die Funktion scheiterte erst mitten im Zeichnen.
    daten["uebergewicht"] = daten["anteil_spaet"] - daten["anteil_frueh"]
    spanne = daten["uebergewicht"].abs().quantile(0.95) or 1.0

    karte = grundkarte(location=[daten["lat"].mean(), daten["lon"].mean()],
                       zoom_start=zoom)
    gruppen = {
        "spaet": folium.FeatureGroup(name="überwiegend zu spät", show=True),
        "frueh": folium.FeatureGroup(name="überwiegend zu früh", show=True),
    }

    for zeile in daten.itertuples():
        folium.CircleMarker(
            location=[zeile.lat, zeile.lon],
            radius=radius_gestuft(zeile.anteil_ausserhalb),
            color="#455A64", weight=1, fill=True,
            fill_color=divergierende_farbe(zeile.uebergewicht, spanne),
            fill_opacity=0.85,
            tooltip=(f"<b>{zeile.stop_name}</b><br>"
                     f"außerhalb des Fensters: "
                     f"<b>{zeile.anteil_ausserhalb:.1f} %</b><br>"
                     f"davon zu früh: {zeile.anteil_frueh:.1f} %<br>"
                     f"davon zu spät: {zeile.anteil_spaet:.1f} %<br>"
                     f"Ø Verspätung: {zeile.avg_delay_s:.1f} s<br>"
                     f"n: {int(zeile.count):,}"),
        ).add_to(gruppen["spaet" if zeile.uebergewicht >= 0 else "frueh"])

    for gruppe in gruppen.values():
        gruppe.add_to(karte)
    folium.LayerControl(collapsed=False).add_to(karte)
    karte.get_root().html.add_child(folium.Element(legende(
        titel=titel,
        bloecke=[
            ("Farbe — welche Richtung überwiegt", [
                (punkt(FARBE_FRUEH),   "überwiegend zu früh"),
                (punkt(FARBE_NEUTRAL), "beide Richtungen gleich"),
                (punkt(FARBE_SPAET),   "überwiegend zu spät"),
            ]),
            ("Kreisgröße — außerhalb des Pünktlichkeitsfensters",
             stufen_legende()),
        ],
        fuss=_fussnote_fenster(schwelle_frueh_s, schwelle_spaet_s),
    )))
    return karte, daten


# Netzfarben fuer die gemeinsame Karte. Bewusst DIESELBEN wie im
# Balkendiagramm aus src/analysis/grafiken.py.
#
# Auf den Einzelnetzkarten waere Rot/Blau falsch — dort traegt die Farbe die
# Richtung (zu frueh / zu spaet), und blaue Punkte auf einer reinen Tramkarte
# haette man als U-Bahn-Stationen lesen koennen. Auf der gemeinsamen Karte ist
# genau umgekehrt Rot/Blau richtig: Beide Netze sind im Bild, Blau IST die
# U-Bahn, und die Karte spricht dieselbe Farbsprache wie das Balkendiagramm.
#
# Geprueft: Abstand 26,4 unter Protanopie, 36 unter Tritanopie.
FARBE_NETZ = {"Tram": "#E53935", "U-Bahn": "#1E88E5"}


def netzvergleichskarte(je_netz: dict, schwelle_frueh_s: int,
                        schwelle_spaet_s: int,
                        min_abfahrten: int = MIN_ABFAHRTEN, zoom: int = 11):
    """Beide Netze auf einer Karte: Farbe = Netz, Groesse = Anteil ausserhalb.

    `je_netz` ist {"Tram": DataFrame, "U-Bahn": DataFrame} aus
    anteile_je_haltestelle().

    ── Warum hier keine Richtungsfarbe ──────────────────────────────────────
    Zwei kategoriale Farbbedeutungen auf einer Karte sind nicht lesbar. Die
    Richtung (zu frueh / zu spaet) bleibt deshalb den Einzelnetzkarten
    vorbehalten; hier traegt die Farbe das Netz, weil das die Aussage ist.

    ── Warum keine Formkodierung ────────────────────────────────────────────
    Naheliegend waere, das Netz zusaetzlich ueber die Form zu unterscheiden
    (Kreis gegen Quadrat, oder gerade gegen 45 Grad gedreht). Das traegt hier
    nicht: 166 der 169 U-Bahn-Stationen liegen in der kleinsten Groessenstufe,
    und bei 5 Pixeln ist ein Quadrat von einem Kreis nicht zu unterscheiden.
    Form wirkt nur bei grossen Symbolen — also genau dort, wo die U-Bahn keine
    hat. Die Farbe traegt die Unterscheidung allein und besteht die
    Farbfehlsichtigkeitspruefung.

    ── Zeichenreihenfolge, zweistufig ───────────────────────────────────────
    An Umsteigepunkten wie U Rosa-Luxemburg-Platz oder U Eberswalder Str.
    liegen Tramhalt und U-Bahn-Station bei **0 m** Abstand exakt uebereinander.
    Ohne Vorkehrung verschwindet der kleine blaue Punkt unter dem grossen roten,
    und die Karte zeigt die U-Bahn ausgerechnet dort nicht, wo der Vergleich am
    schaerfsten ist. Zwei Dinge sorgen dafuer, dass das nicht passiert:

    1. INNERHALB eines Netzes werden grosse Kreise zuerst gezeichnet.
    2. ZWISCHEN den Netzen entscheidet die Reihenfolge der Leaflet-Ebenen, denn
       jedes Netz ist eine eigene FeatureGroup — die zuletzt hinzugefuegte
       liegt oben. Das Netz mit den kleineren Kreisen kommt deshalb zuletzt,
       ermittelt aus den Daten und nicht aus der Reihenfolge im Dictionary.

    ── Was diese Karte NICHT zeigt ──────────────────────────────────────────
    Die Netze ueberlappen sich raeumlich kaum: Der Median-Abstand einer
    U-Bahn-Station zum naechsten Tramhalt betraegt 2,6 km, 59 % liegen weiter
    als 2 km entfernt, die Schwerpunkte sind 7,9 km auseinander (Tram Osten,
    U-Bahn Westen). Die Karte stellt deshalb ueberwiegend zwei benachbarte
    Gebiete nebeneinander, nicht denselben Ort zweimal. Wer aus ihr allein
    schliesst, ist gegen den Einwand "das ist Ost gegen West, nicht Tram gegen
    U-Bahn" wehrlos. Die Antwort darauf liefert `gepaarte_standorte()`.
    """
    import folium

    karte = None
    marker = []
    for netz, stops in je_netz.items():
        daten = stops[stops["count"] >= min_abfahrten]
        for zeile in daten.itertuples():
            marker.append((radius_gestuft(zeile.anteil_ausserhalb), netz, zeile))

    mitte_lat = sum(m[2].lat for m in marker) / len(marker)
    mitte_lon = sum(m[2].lon for m in marker) / len(marker)
    karte = grundkarte(location=[mitte_lat, mitte_lon], zoom_start=zoom)
    gruppen = {netz: folium.FeatureGroup(name=netz, show=True)
               for netz in je_netz}

    for radius, netz, zeile in sorted(marker, key=lambda m: -m[0]):
        folium.CircleMarker(
            location=[zeile.lat, zeile.lon], radius=radius,
            color="#37474F", weight=1, fill=True,
            fill_color=FARBE_NETZ[netz], fill_opacity=0.85,
            tooltip=(f"<b>{zeile.stop_name}</b><br>{netz}<br>"
                     f"außerhalb des Fensters: "
                     f"<b>{zeile.anteil_ausserhalb:.1f} %</b><br>"
                     f"davon zu früh: {zeile.anteil_frueh:.1f} %<br>"
                     f"davon zu spät: {zeile.anteil_spaet:.1f} %<br>"
                     f"n: {int(zeile.count):,}"),
        ).add_to(gruppen[netz])

    # Netz mit den kleineren Kreisen zuletzt hinzufuegen, damit es oben liegt.
    mittlerer_radius = {
        netz: sum(r for r, n, _ in marker if n == netz)
              / max(sum(1 for _, n, _ in marker if n == netz), 1)
        for netz in je_netz
    }
    for netz in sorted(gruppen, key=lambda n: -mittlerer_radius[n]):
        gruppen[netz].add_to(karte)
    folium.LayerControl(collapsed=False).add_to(karte)
    karte.get_root().html.add_child(folium.Element(legende(
        titel="Tram gegen U-Bahn",
        bloecke=[
            ("Farbe — Netz", [(punkt(FARBE_NETZ[n]), n) for n in je_netz]),
            ("Kreisgröße — außerhalb des Pünktlichkeitsfensters",
             stufen_legende()),
        ],
        fuss=_fussnote_fenster(schwelle_frueh_s, schwelle_spaet_s),
    )))
    return karte


def _bahnhofskern(name: str) -> str:
    """Reduziert einen Haltestellennamen auf den Bahnhof, den er meint.

        `S+U Alexanderplatz Bhf/Gontardstr. (Berlin)` → `Alexanderplatz`
        `U Naturkundemuseum (Berlin) [Invalidenstr.]` → `Naturkundemuseum`

    Damit fallen die vier Alexanderplatz-Bahnsteige der Tram auf denselben
    Schluessel wie die U-Bahn-Station.
    """
    import re
    n = re.sub(r"\[.*?\]", "", name).replace("(Berlin)", "").strip()
    n = re.sub(r"^(S\+U|U)\s+", "", n).split("/")[0].strip().rstrip(",")
    return re.sub(r"\s+Bhf$", "", n).strip()


def gemeinsame_standorte(tram, ubahn, min_abfahrten: int = MIN_ABFAHRTEN):
    """Orte, an denen beide Netze halten — erkannt am NAMEN, nicht am Abstand.

    Rueckgabe wie `gepaarte_standorte()`: eine Zeile je Ort, mit denselben
    Spalten, damit `netzvergleichskarte_gepaart()` unveraendert damit zeichnet.

    ── Warum diese Funktion die aeltere abloest ─────────────────────────────

    `gepaarte_standorte()` nimmt zu jeder U-Bahn-Station den naechsten Tramhalt
    im Umkreis von 300 m. Das erzeugt drei Paare, die keine sind:

        U Unter den Linden  ← Universitaetsstr.            292 m
        U Turmstr.          ← Luebecker Str.               279 m
        U Rotes Rathaus     ← Spandauer Str./Marienkirche  231 m

    Das sind Nachbarhaltestellen, keine Umsteigepunkte. An U Turmstr. faehrt im
    Erhebungszeitraum ueberhaupt keine Tram — die M10 endet an Luebecker Str.,
    eine Station davor. Wer diese drei mitzaehlt, vergleicht wieder zwei Orte
    statt einen; genau das soll die Auswahl ja ausschliessen.

    Der Abstand hat einen zweiten, unauffaelligeren Fehler: Er nimmt je Station
    **einen** Tramhalt. Am Alexanderplatz war das der Bahnsteig Dircksenstr.
    mit 16.550 Abfahrten — Gontardstr. (81.083) und Memhardstr. (34.567)
    fielen heraus, obwohl sie derselbe Ort sind. Die Tramseite stand dort also
    auf einem Achtel der verfuegbaren Abfahrten.

    ── Die Regel ───────────────────────────────────────────────────────────

    Die BVG benennt den Tramhalt am Umsteigepunkt nach der U-Bahn-Station:
    `U Eberswalder Str.`, `S+U Pankow`, `U Tierpark`. Gezaehlt wird ein Ort
    deshalb genau dann, wenn ein Tramhalt das Praefix `U ` oder `S+U ` traegt
    und sein Bahnhofskern zu einer U-Bahn-Station passt. Alle passenden
    Bahnsteige gehen mengengewichtet in die Tramseite ein.

    Das braucht keinen frei gewaehlten Radius und findet 21 Orte statt 24.

    ── Wo der Trampunkt liegt ──────────────────────────────────────────────

    Beim Ergebnis mehrerer Bahnsteige wird der mengengewichtete Mittelpunkt
    gezeichnet, nicht einer der Bahnsteige. Der gezeichnete Punkt gehoert dann
    zu demselben Wert, den der Tooltip nennt — ein einzelner Bahnsteig als Ort
    wuerde eine Genauigkeit vortaeuschen, die der Mittelwert nicht hat.
    """
    import re

    import pandas as pd

    t = tram[tram["count"] >= min_abfahrten]
    u = ubahn[ubahn["count"] >= min_abfahrten]
    stationen = {_bahnhofskern(r.stop_name): r for r in u.itertuples()}

    gruppen: dict = {}
    for halt in t.itertuples():
        if not re.match(r"^(S\+U|U)\s+", halt.stop_name):
            continue
        kern = _bahnhofskern(halt.stop_name)
        if kern in stationen:
            gruppen.setdefault(kern, []).append(halt)

    zeilen = []
    for kern, halte in gruppen.items():
        station = stationen[kern]
        n = sum(h.count for h in halte)
        mittel = lambda feld: sum(  # noqa: E731 — nur hier, mengengewichtet
            getattr(h, feld) * h.count for h in halte) / n
        tram_lat, tram_lon = mittel("lat"), mittel("lon")
        zeilen.append({
            "station": station.stop_name,
            "ubahn_pct": station.anteil_ausserhalb,
            # Bei mehreren Bahnsteigen nennt die Beschriftung ihre Zahl, nicht
            # eine willkuerlich herausgegriffene Adresse.
            "tramhalt": (halte[0].stop_name if len(halte) == 1
                         else f"{kern} ({len(halte)} Tramhalte)"),
            "tram_pct": mittel("anteil_ausserhalb"),
            "abstand_m": min(
                _abstand_m(station.lat, station.lon, h.lat, h.lon)
                for h in halte),
            "ubahn_lat": station.lat, "ubahn_lon": station.lon,
            "ubahn_frueh": station.anteil_frueh,
            "ubahn_spaet": station.anteil_spaet,
            "ubahn_n": int(station.count),
            "tram_lat": tram_lat, "tram_lon": tram_lon,
            "tram_frueh": mittel("anteil_frueh"),
            "tram_spaet": mittel("anteil_spaet"),
            "tram_n": int(n),
        })

    df = pd.DataFrame(zeilen)
    if not df.empty:
        df["differenz_pp"] = df["tram_pct"] - df["ubahn_pct"]
        df = df.sort_values("differenz_pp", ascending=False).reset_index(drop=True)
    return df


def _abstand_m(lat1, lon1, lat2, lon2) -> float:
    """Abstand in Metern, fuer Berlin genau genug."""
    import math
    return math.hypot((lat1 - lat2) * 111_320,
                      (lon1 - lon2) * 111_320 * math.cos(math.radians(lat1)))


def gepaarte_standorte(tram, ubahn, radius_m: float = 300,
                       min_abfahrten: int = MIN_ABFAHRTEN):
    """U-Bahn-Stationen mit einem Tramhalt in Reichweite — der gepaarte Vergleich.

    ── ABGELOEST, 21.08.2026 ────────────────────────────────────────────────
    Fuer die Karten und die Animation zaehlt jetzt `gemeinsame_standorte()`,
    das ueber den Namen geht statt ueber den Abstand. Die Begruendung steht
    dort; kurz: Drei der 24 Paare sind Nachbarhaltestellen und keine
    Umsteigepunkte, und die Tramseite stand je Ort auf nur einem Bahnsteig.
    Diese Funktion bleibt fuer die Notebooks stehen, die sie zitieren.

    Die gemeinsame Karte hat ein Konfundierungsproblem: Tram und U-Bahn
    bedienen weitgehend verschiedene Stadthaelften, also vergleicht man mit ihr
    auch Ost gegen West. Diese Funktion loest das, indem sie nur Standorte
    heranzieht, an denen beide Netze **denselben Ort** bedienen — viele Paare
    liegen bei 0 m Abstand, es ist derselbe Umsteigepunkt.

    Gleiche Lage, gleiche Fahrgaeste, gleiche Stadtstruktur, gleicher Zeitraum:
    Was uebrig bleibt, ist das Verkehrsmittel.

    Rueckgabe: DataFrame mit einer Zeile je Paar. Die Zeile traegt neben den
    beiden Anteilen auch Koordinaten, Richtungsanteile und Fallzahlen beider
    Seiten mit — damit netzvergleichskarte_gepaart() dieselbe Zeile zeichnet,
    die auch in der Tabelle steht, und Karte und Tabelle nicht auseinander
    laufen koennen.
    """
    import numpy as np
    import pandas as pd

    t = tram[tram["count"] >= min_abfahrten].reset_index(drop=True)
    u = ubahn[ubahn["count"] >= min_abfahrten]
    breite, laenge = t["lat"].to_numpy(), t["lon"].to_numpy()

    zeilen = []
    for station in u.itertuples():
        d = np.sqrt(((breite - station.lat) * 111_320) ** 2
                    + ((laenge - station.lon) * 111_320
                       * np.cos(np.radians(station.lat))) ** 2)
        i = int(d.argmin())
        if d[i] > radius_m:
            continue
        zeilen.append({
            "station": station.stop_name,
            "ubahn_pct": station.anteil_ausserhalb,
            "tramhalt": t.loc[i, "stop_name"],
            "tram_pct": t.loc[i, "anteil_ausserhalb"],
            "abstand_m": float(d[i]),
            "ubahn_lat": station.lat, "ubahn_lon": station.lon,
            "ubahn_frueh": station.anteil_frueh,
            "ubahn_spaet": station.anteil_spaet,
            "ubahn_n": int(station.count),
            "tram_lat": float(t.loc[i, "lat"]), "tram_lon": float(t.loc[i, "lon"]),
            "tram_frueh": float(t.loc[i, "anteil_frueh"]),
            "tram_spaet": float(t.loc[i, "anteil_spaet"]),
            "tram_n": int(t.loc[i, "count"]),
        })

    df = pd.DataFrame(zeilen)
    if not df.empty:
        df["differenz_pp"] = df["tram_pct"] - df["ubahn_pct"]
        df = df.sort_values("differenz_pp", ascending=False).reset_index(drop=True)
    return df


def netzvergleichskarte_gepaart(paare, schwelle_frueh_s: int,
                                schwelle_spaet_s: int):
    """Nur die Orte, die sich beide Netze teilen — die Antwort auf Ost gegen West.

    Gleiche Farben, gleiche Kreisstufen, gleiche Legende wie
    netzvergleichskarte(); der Unterschied ist ausschliesslich die Auswahl.
    Gezeichnet wird direkt aus dem Ergebnis von `gepaarte_standorte()`, also
    aus derselben Zeile, die auch in der Tabelle der Szene 9c steht.

    ── Warum diese Fassung neben der vollen existiert ───────────────────────
    Die volle Karte zeigt 396 Tramhalte gegen 169 U-Bahn-Stationen und damit
    ueberwiegend zwei benachbarte Gebiete: Tram im Osten, U-Bahn im Westen,
    Median-Abstand 2,6 km. Wer aus ihr allein schliesst, ist gegen den Einwand
    "das ist Ost gegen West, nicht Tram gegen U-Bahn" wehrlos. Diese Karte
    nimmt genau den Einwand vorweg — sie zeigt nur die Standorte, an denen
    beide Netze denselben Ort bedienen, und dort steht der Unterschied ohne
    Geografie im Bild.

    ── Die Kreise liegen absichtlich uebereinander ──────────────────────────
    Viele Paare liegen bei **0 m** Abstand, es ist derselbe Umsteigepunkt. Die
    beiden Kreise werden nicht auseinandergezogen — verschobene Punkte waeren
    eine falsche Ortsangabe, und die Ueberlagerung ist hier die Aussage: Der
    blaue Punkt sitzt im roten, und was rot herausschaut, ist der Abstand
    zwischen den Netzen an dieser einen Strassenecke.

    Damit das sichtbar bleibt, wird je Paar zuerst der groessere Kreis
    gezeichnet. Anders als bei der vollen Karte entscheidet das nicht die
    Ebenenreihenfolge, sondern die Reihenfolge innerhalb einer gemeinsamen
    Gruppe — bei 24 Paaren ist das ueberschaubar, und an den zwei Paaren, an
    denen die U-Bahn schlechter ist, liegt dann eben Rot oben.

    ── Verbindungslinie ─────────────────────────────────────────────────────
    Paare ueber 40 m Abstand bekommen eine duenne Linie. Auf der Uebersicht
    sieht man sie nicht, beim Hineinzoomen belegt sie, welcher Tramhalt zu
    welcher Station gehoert. Unter 40 m waere sie kuerzer als die Kreise.

    ── Was hier doppelt sein kann ───────────────────────────────────────────
    Ein Tramhalt kann der naechste zu zwei U-Bahn-Stationen sein und wird dann
    zweimal gezeichnet — an derselben Stelle, also unsichtbar. Die Paarzahl in
    der Legende zaehlt Paare, nicht verschiedene Halte.
    """
    import folium

    if paare.empty:
        raise ValueError("keine gepaarten Standorte — Radius zu klein?")

    gruppe = folium.FeatureGroup(name="gepaarte Standorte", show=True)
    linien = folium.FeatureGroup(name="Zuordnung", show=True)
    ecken = []

    for paar in paare.itertuples():
        if paar.abstand_m > 40:
            folium.PolyLine(
                [(paar.tram_lat, paar.tram_lon), (paar.ubahn_lat, paar.ubahn_lon)],
                color="#90A4AE", weight=2, opacity=0.9, dash_array="4,4",
            ).add_to(linien)

        kreise = [
            ("Tram", paar.tramhalt, paar.tram_lat, paar.tram_lon,
             paar.tram_pct, paar.tram_frueh, paar.tram_spaet, paar.tram_n),
            ("U-Bahn", paar.station, paar.ubahn_lat, paar.ubahn_lon,
             paar.ubahn_pct, paar.ubahn_frueh, paar.ubahn_spaet, paar.ubahn_n),
        ]
        # Groesserer Kreis zuerst, damit der kleinere nicht darunter verschwindet.
        #
        # An zwei Orten reicht das nicht: Warschauer Str. (Tram 2,8 %, U-Bahn
        # 0,0 %) und Lichtenberg (0,7 % gegen 2,9 %) fallen mit BEIDEN Werten in
        # dieselbe Groessenstufe, und bei 0 m Abstand deckt der zuletzt
        # gezeichnete Kreis den ersten exakt ab. Sichtbar ist dort nur ein Netz.
        # Das bleibt am 21.08.2026 auf Wunsch der Nutzerin so.
        #
        # ACHTUNG BEIM ABLESEN: Der sichtbare Kreis ist der mit dem KLEINEREN
        # Anteil, nicht der schlechtere. An Lichtenberg ist die U-Bahn
        # tatsaechlich schlechter; an Warschauer Str. ist es die Tram (2,8 %
        # gegen 0,0 %) — sie liegt nur unter dem blauen Punkt.
        for netz, name, lat, lon, ausserhalb, frueh, spaet, n in sorted(
                kreise, key=lambda k: -k[4]):
            ecken.append((lat, lon))
            folium.CircleMarker(
                location=[lat, lon], radius=radius_gestuft(ausserhalb),
                color="#37474F", weight=1, fill=True,
                fill_color=FARBE_NETZ[netz], fill_opacity=0.85,
                tooltip=(f"<b>{name}</b><br>{netz}<br>"
                         f"außerhalb des Fensters: <b>{ausserhalb:.1f} %</b><br>"
                         f"davon zu früh: {frueh:.1f} %<br>"
                         f"davon zu spät: {spaet:.1f} %<br>"
                         f"n: {n:,}<br>"
                         f"<i>Paar: {paar.station} ↔ {paar.tramhalt}, "
                         f"{paar.abstand_m:.0f} m — Differenz "
                         f"{paar.differenz_pp:+.1f} pp</i>"),
            ).add_to(gruppe)

    karte = grundkarte()
    linien.add_to(karte)
    gruppe.add_to(karte)
    # Kein fester Zoom: Die Auswahl ist klein und liegt anders als das volle
    # Netz nicht um die Stadtmitte herum. Der Ausschnitt kommt deshalb aus den
    # Punkten selbst, sonst haengt die halbe Auswahl ausserhalb des Bildes.
    karte.fit_bounds(
        [[min(e[0] for e in ecken), min(e[1] for e in ecken)],
         [max(e[0] for e in ecken), max(e[1] for e in ecken)]],
        padding=(60, 60))
    folium.LayerControl(collapsed=False).add_to(karte)

    schlechter = int((paare["differenz_pp"] > 0).sum())
    karte.get_root().html.add_child(folium.Element(legende(
        titel="Dieselbe Straßenecke",
        bloecke=[
            ("Farbe — Netz", [(punkt(FARBE_NETZ[n]), n)
                              for n in ("Tram", "U-Bahn")]),
            ("Kreisgröße — außerhalb des Pünktlichkeitsfensters",
             stufen_legende()),
        ],
        fuss=(f"Nur die {len(paare)} Standorte, an denen ein Tramhalt denselben "
              "Bahnhofsnamen trägt wie die U-Bahn-Station; die meisten liegen "
              f"bei 0 m. An {schlechter} von {len(paare)} ist die Tram "
              "schlechter. Gleiche Lage, gleicher Zeitraum — was übrig bleibt, "
              "ist das Verkehrsmittel. "
              + _fussnote_fenster(schwelle_frueh_s, schwelle_spaet_s)),
    )))
    return karte


def lsa_statuskarte(stops, schwelle_frueh_s: int, schwelle_spaet_s: int,
                    min_abfahrten: int = MIN_ABFAHRTEN, zoom: int = 12):
    """Gleiche Geometrie und Kreisgroesse, Farbe nach ÖPNV-Beeinflussung.

    Eine eigene Datei statt einer umschaltbaren Ebene: Vor der Kamera will man
    nicht klicken muessen, und beim Schnitt bewegt sich so nichts ausser der
    Faerbung.
    """
    import folium

    daten = stops[stops["count"] >= min_abfahrten].copy()
    karte = grundkarte(location=[daten["lat"].mean(), daten["lon"].mean()],
                       zoom_start=zoom)
    gruppen = {
        "aktiv":    folium.FeatureGroup(name="Beeinflussung aktiv", show=True),
        "inaktiv":  folium.FeatureGroup(name="Beeinflussung inaktiv", show=True),
        "kein_lsa": folium.FeatureGroup(name="keine Anlage im Radius", show=True),
    }

    for zeile in daten.itertuples():
        # "nicht_vorhanden" ist seit der Korrektur gegen Drs. 19/19804 leer;
        # der Zweig bleibt stehen, falls der Index wieder Werte liefert.
        status = getattr(zeile, "lsa_status", "kein_lsa")
        schluessel = ("inaktiv" if status in ("inaktiv", "nicht_vorhanden")
                      else "aktiv" if status == "aktiv" else "kein_lsa")
        folium.CircleMarker(
            location=[zeile.lat, zeile.lon],
            radius=radius_gestuft(zeile.anteil_ausserhalb),
            color="#455A64", weight=1, fill=True,
            fill_color=FARBE_LSA[schluessel], fill_opacity=0.8,
            tooltip=(f"<b>{zeile.stop_name}</b><br>"
                     f"außerhalb des Fensters: "
                     f"<b>{zeile.anteil_ausserhalb:.1f} %</b><br>"
                     f"LSA-Status: {status}<br>"
                     f"n: {int(zeile.count):,}"),
        ).add_to(gruppen[schluessel])

    for gruppe in gruppen.values():
        gruppe.add_to(karte)
    folium.LayerControl(collapsed=False).add_to(karte)
    karte.get_root().html.add_child(folium.Element(legende(
        titel="ÖPNV-Beeinflussung",
        bloecke=[
            ("Farbe — Status der Anlage", [
                (punkt(FARBE_LSA["aktiv"]),    "Beeinflussung aktiv"),
                (punkt(FARBE_LSA["inaktiv"]),  "Beeinflussung inaktiv"),
                (punkt(FARBE_LSA["kein_lsa"]), "keine Anlage im Umkreis 150 m"),
            ]),
            ("Kreisgröße — außerhalb des Pünktlichkeitsfensters",
             stufen_legende()),
        ],
        fuss=("Status aus Abgeordnetenhaus Berlin, Drs. 19/19804. Der offene "
              "Datensatz enthält nur Lage und Bezeichnung, keinen ÖPNV-Status. "
              + _fussnote_fenster(schwelle_frueh_s, schwelle_spaet_s)),
    )))
    return karte, daten
