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
#     Tuerkis #0097A7 gegen Orange #E65100
#     Chroma bestanden, Kontrast bestanden,
#     Abstand unter Protanopie 19,0 — unter Tritanopie 35,2 (Grenze 8)
#
# Die Bedeutung ist auf beiden Karten dieselbe und darf nicht getauscht werden:
#
#     TUERKIS = die harmlosere Richtung im Bild (zu frueh / baut Verspaetung ab)
#     ORANGE  = die Richtung, um die es in der Handlungsempfehlung geht
#               (zu spaet / erzeugt Verspaetung)

FARBE_FRUEH = "#0097A7"   # tuerkis — ueberwiegend zu frueh / baut Verspaetung ab
FARBE_SPAET = "#E65100"   # orange  — ueberwiegend zu spaet / erzeugt Verspaetung
FARBE_NEUTRAL = "#B0BEC5"  # grau    — Mittelpunkt der divergierenden Skala

# Farben der LSA-Zuordnung. Unveraendert aus der bisherigen Kartenzelle
# uebernommen, damit die eingefaerbte Fassung wie gehabt aussieht.
FARBE_LSA = {
    "aktiv":    "#43A047",
    "inaktiv":  "#E53935",
    "kein_lsa": "#9E9E9E",
}


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
# "die grossen Kreise sind die Halte mit ueber 40 Prozent". Zusaetzlich haengt
# das Bild damit nicht mehr am 95. Perzentil der gerade geladenen Daten — bei
# laufender Erhebung wanderte die Skala sonst bei jedem Durchlauf.
#
# (Untergrenze in Prozentpunkten, Radius in Pixeln)
STUFEN_ANTEIL = [(0, 5), (10, 9), (20, 13), (30, 18), (40, 24)]


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
                           max_haltestellen: int = 2000):
    """Je Haltestelle: Anteil zu frueher, zu spaeter und ausserhalb liegender
    Abfahrten, dazu Koordinaten, Mittelwert und Fallzahl.

    Eine einzige Aggregation. Nenner ist ueberall die Zahl der Abfahrten MIT
    Echtzeitwert — die Filter koennen nur solche Dokumente treffen, ein anderer
    Nenner wuerde die Anteile systematisch kleinrechnen.
    """
    import pandas as pd

    antwort = es.search(
        index=index, size=0,
        aggs={"stops": {
            "terms": {"field": "stop_name", "size": max_haltestellen},
            "aggs": {
                "avg_delay": {"avg": {"field": "delay_s"}},
                "n_delay":   {"value_count": {"field": "delay_s"}},
                "zu_frueh":  {"filter": {"range": {
                    "delay_s": {"lte": schwelle_frueh_s}}}},
                "zu_spaet":  {"filter": {"range": {
                    "delay_s": {"gte": schwelle_spaet_s}}}},
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
        frueh = eimer["zu_frueh"]["doc_count"] / n * 100
        spaet = eimer["zu_spaet"]["doc_count"] / n * 100
        zeilen.append({
            "stop_name": eimer["key"],
            "lat": ort["lat"], "lon": ort["lon"],
            "avg_delay_s": eimer["avg_delay"]["value"],
            "count": n,
            "anteil_frueh": frueh,
            "anteil_spaet": spaet,
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

    SPAET — "mehr als 210 s" liegt EXAKT ZWISCHEN den Rasterstufen 180 und 240.
    Es gibt hier also keine getreue Umsetzung: >= 240 zaehlt weniger als der
    Vertrag, >= 180 zaehlt mehr. Die 180 ist eine bewusste Verschaerfung und
    darf nicht als Rundungsfolge ausgegeben werden.

    Gegenprobe, damit die Wahl nicht das Ergebnis traegt: Der Abstand zwischen
    den Netzen betraegt bei 180 s das 2,65-fache und bei 240 s das 2,90-fache —
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

    if schwelle_spaet_s == 180:
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

    karte = folium.Map(location=[daten["lat"].mean(), daten["lon"].mean()],
                       zoom_start=zoom, tiles="CartoDB positron")
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
    karte = folium.Map(location=[mitte_lat, mitte_lon], zoom_start=zoom,
                       tiles="CartoDB positron")
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


def gepaarte_standorte(tram, ubahn, radius_m: float = 300,
                       min_abfahrten: int = MIN_ABFAHRTEN):
    """U-Bahn-Stationen mit einem Tramhalt in Reichweite — der gepaarte Vergleich.

    Die gemeinsame Karte hat ein Konfundierungsproblem: Tram und U-Bahn
    bedienen weitgehend verschiedene Stadthaelften, also vergleicht man mit ihr
    auch Ost gegen West. Diese Funktion loest das, indem sie nur Standorte
    heranzieht, an denen beide Netze **denselben Ort** bedienen — viele Paare
    liegen bei 0 m Abstand, es ist derselbe Umsteigepunkt.

    Gleiche Lage, gleiche Fahrgaeste, gleiche Stadtstruktur, gleicher Zeitraum:
    Was uebrig bleibt, ist das Verkehrsmittel.

    Rueckgabe: DataFrame mit einer Zeile je Paar.
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
        })

    df = pd.DataFrame(zeilen)
    if not df.empty:
        df["differenz_pp"] = df["tram_pct"] - df["ubahn_pct"]
        df = df.sort_values("differenz_pp", ascending=False).reset_index(drop=True)
    return df


def lsa_statuskarte(stops, schwelle_frueh_s: int, schwelle_spaet_s: int,
                    min_abfahrten: int = MIN_ABFAHRTEN, zoom: int = 12):
    """Gleiche Geometrie und Kreisgroesse, Farbe nach ÖPNV-Beeinflussung.

    Eine eigene Datei statt einer umschaltbaren Ebene: Vor der Kamera will man
    nicht klicken muessen, und beim Schnitt bewegt sich so nichts ausser der
    Faerbung.
    """
    import folium

    daten = stops[stops["count"] >= min_abfahrten].copy()
    karte = folium.Map(location=[daten["lat"].mean(), daten["lon"].mean()],
                       zoom_start=zoom, tiles="CartoDB positron")
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
