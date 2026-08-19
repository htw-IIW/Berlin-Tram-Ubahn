#!/usr/bin/env python3
"""Schreibt die Validierungsgrafik als Klickanimation für den Videoschnitt.

    python3 scripts/animation_validierung.py
    open video/animation/validierung_puenktlichkeit.html

Erzeugt eine eigenständige HTML-Datei (plotly ist eingebettet, kein Internet
nötig). Das Bild beginnt **weiß**; jeder Klick blendet einen Schritt ein:

    1. die Überschrift
    2. der Hinweis „Monitor misst je Fahrt — ich messe je Halt"
    3. meine Messung, Tram gegen U-Bahn
    4. die amtliche Messung daneben, blass

Zurück geht es mit Rücktaste oder Pfeil links — praktisch, wenn eine Aufnahme
wiederholt werden muss. Die Leertaste wirkt wie ein Klick.

Gezeigt wird nur die **Pünktlichkeit**. Die Ausfälle sind an dieser Stelle der
Storyline noch nicht eingeführt und lenken ab; die Zeichenlogik kann sie über
`--kennzahl ausgefallen`.

Zahlen und Zeichenlogik kommen aus denselben Quellen wie die PNG-Fassung:
`werte_fuer()` in scripts/grafik_validierung.py und `validierung_animation()` in
src/analysis/grafiken.py. Beschriftungen ändert man dort in `TEXTE_ANIMATION`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from elasticsearch import Elasticsearch                         # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER       # noqa: E402
from src.analysis.grafiken import (                             # noqa: E402
    RAND_LINKS, RAND_RECHTS, RAND_UNTEN, TEXTE_ANIMATION,
    validierung_animation,
)

from grafik_validierung import werte_fuer                       # noqa: E402

# video/animationen/ — mit -en. Dort liegen die Animationen der
# Videoschnitt-Sitzung (lsa-vorrang, puenktlichkeitsfenster, …), und dieselbe
# Datei zweimal in zwei aehnlich benannten Ordnern ist eine Falle.
STANDARDZIEL = WURZEL / "video" / "animationen" / "validierung_puenktlichkeit.html"

# Der Block wird an das von plotly erzeugte HTML angehaengt.
#
# Die Balken fahren von null hoch — nicht ueber Plotly.animate, sondern ueber
# eine eigene Schleife mit requestAnimationFrame. Grund: plotlys Uebergaenge
# greifen bei Balkendiagrammen nicht zuverlaessig, und ein Balken, der bei einem
# Teil der Laeufe springt statt zu wachsen, ist im Video unbrauchbar. Die
# Schleife setzt einfach 60-mal je Sekunde neue Hoehen.
#
# Die Prozentzahl erscheint ERST NACH dem Hochfahren. Waehrend ein Balken
# waechst, wandert seine Beschriftung sonst mit nach oben und zieht den Blick
# von der Hoehe weg.
SKRIPT = """
<style>
  html, body {{ margin: 0; padding: 0; background: #ffffff; }}
  #{div_id} {{ width: 100vw; height: 100vh; }}

  /* Die Differenzzeile.
     Sie liegt UEBER der Grafik statt darin — als plotly-Annotation ist sie mit
     den Achsenbeschriftungen kollidiert, sobald die Kategorien schraeg standen.
     Als eigenes Element kann nichts verrutschen.

     Die Ausrichtung haengt an drei Zahlen, die aus dem Layout der Figur kommen:
     linker Rand, rechter Rand, unterer Rand. Zwischen den Raendern liegt die
     Zeichenflaeche; zwei gleich breite Zellen darin treffen genau die Mitte der
     beiden Balkengruppen. */
  #differenz {{
    position: fixed; left: 0; right: 0; bottom: {zeile_unten}px;
    display: flex; align-items: baseline;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue",
      Helvetica, Arial, sans-serif;
    opacity: 0; transition: opacity .45s ease-out;
    pointer-events: none;
  }}
  #differenz .beschriftung {{
    width: {rand_links}px; padding-right: 18px; box-sizing: border-box;
    text-align: right; font-size: 22px; color: #90A4AE;
  }}
  #differenz .werte {{
    flex: 1; margin-right: {rand_rechts}px; display: flex;
  }}
  #differenz .werte span {{
    flex: 1; text-align: center;
    font-size: 40px; font-weight: 700; color: #37474F;
  }}

  #hinweis {{
    position: fixed; right: 18px; bottom: 14px;
    font: 15px/1.4 system-ui, sans-serif; color: #b0bec5;
    pointer-events: none; transition: opacity .4s;
  }}
</style>
<div id="differenz">
  <div class="beschriftung">{beschriftung_differenz}</div>
  <div class="werte">{zellen}</div>
</div>
<div id="hinweis">Klicken zum Aufbauen · ← zurück · Home auf Anfang</div>
<script>
  (function () {{
    var gd = document.getElementById({div_id_json});
    var schritte = {schritte};
    var ANZAHL_TRACES = {anzahl_traces};
    var ANZAHL_X = {anzahl_x};
    var ANZAHL_ANNOTATIONEN = {anzahl_annotationen};
    var DAUER_MS = {dauer_ms};

    var stand = 0;
    var laeuft = false;      // sperrt Klicks waehrend des Hochfahrens

    function leer(fuellwert) {{
      var a = [];
      for (var k = 0; k < ANZAHL_TRACES; k++) {{
        var zeile = [];
        for (var i = 0; i < ANZAHL_X; i++) zeile.push(fuellwert);
        a.push(zeile);
      }}
      return a;
    }}

    // Vollstaendiger Zustand nach `bis` Schritten. Immer vom Nullzustand aus
    // aufgebaut — dadurch ist der Rueckwaertsweg derselbe Code wie der
    // Vorwaertsweg, und Zustaende koennen sich nicht aufaddieren.
    function zustandFuer(bis) {{
      var y = leer(null), text = leer(""), differenz = false;
      var layout = {{}};
      for (var a = 0; a < ANZAHL_ANNOTATIONEN; a++) {{
        layout["annotations[" + a + "].visible"] = false;
      }}
      for (var i = 0; i < bis; i++) {{
        var s = schritte[i];
        if (s.layout) Object.assign(layout, s.layout);
        if (s.differenz) differenz = true;
        if (s.balken) {{
          for (var k = 0; k < ANZAHL_TRACES; k++) {{
            y[k][s.balken.i]    = s.balken.y[k];
            text[k][s.balken.i] = s.balken.text[k];
          }}
        }}
      }}
      return {{y: y, text: text, layout: layout, differenz: differenz}};
    }}

    function setzen(z) {{
      Plotly.restyle(gd, {{y: z.y, text: z.text}});
      Plotly.relayout(gd, z.layout);
      var d = document.getElementById("differenz");
      if (d) d.style.opacity = z.differenz ? "1" : "0";
    }}

    function hochfahren(vorher, ziel, balken) {{
      laeuft = true;
      var t0 = null;
      function rahmen(jetzt) {{
        if (t0 === null) t0 = jetzt;
        var p = Math.min((jetzt - t0) / DAUER_MS, 1);
        var e = 1 - Math.pow(1 - p, 3);          // ease-out, kein Nachfedern
        var y = vorher.y.map(function (zeile) {{ return zeile.slice(); }});
        for (var k = 0; k < ANZAHL_TRACES; k++) {{
          y[k][balken.i] = balken.y[k] * e;
        }}
        Plotly.restyle(gd, {{y: y}});
        if (p < 1) {{
          requestAnimationFrame(rahmen);
        }} else {{
          setzen(ziel);                          // jetzt erst die Prozentzahl
          laeuft = false;
        }}
      }}
      requestAnimationFrame(rahmen);
    }}

    function weiter(richtung) {{
      if (laeuft) return;
      var neu = Math.min(Math.max(stand + richtung, 0), schritte.length);
      if (neu === stand) return;

      var vorher = zustandFuer(richtung > 0 ? stand : neu);
      var ziel   = zustandFuer(neu);
      var s      = schritte[neu - 1];

      // Nur vorwaerts wird animiert. Rueckwaerts springt es — beim Wiederholen
      // einer Aufnahme will man sofort im Ausgangszustand sein.
      //
      // Das Layout wird hier absichtlich NICHT vorab gesetzt: Die Zahl unter der
      // Gruppe soll zusammen mit den Prozentzahlen erscheinen, also erst wenn
      // die Balken oben stehen. setzen(ziel) am Ende von hochfahren() erledigt
      // beides in einem Zug.
      if (richtung > 0 && s && s.balken) {{
        hochfahren(vorher, ziel, s.balken);
      }} else {{
        setzen(ziel);
      }}

      stand = neu;
      var h = document.getElementById("hinweis");
      if (h) h.style.opacity = stand === 0 ? "1" : "0";
    }}

    document.addEventListener("click", function () {{ weiter(+1); }});
    document.addEventListener("keydown", function (e) {{
      if (e.key === " " || e.key === "ArrowRight" || e.key === "Enter") {{
        e.preventDefault(); weiter(+1);
      }} else if (e.key === "Backspace" || e.key === "ArrowLeft") {{
        e.preventDefault(); weiter(-1);
      }} else if (e.key === "Home") {{
        e.preventDefault();
        if (laeuft) return;
        stand = 0;
        setzen(zustandFuer(0));
        document.getElementById("hinweis").style.opacity = "1";
      }}
    }});
  }})();
</script>
"""


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--monat", default="Mai 26",
                   help="Monat wie in validierung_bvg.MONATE (Vorgabe: Mai 26)")
    p.add_argument("--kennzahl", default="unpünktlich",
                   choices=["unpünktlich", "ausgefallen"])
    p.add_argument("--dauer", type=int, default=750,
                   help="Wie lange die Balken hochfahren, in Millisekunden "
                        "(Vorgabe: 750)")
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)
    werte = werte_fuer(es, args.monat)

    fig, schritte = validierung_animation(werte, args.kennzahl)

    div_id = "grafik"
    html = fig.to_html(include_plotlyjs=True, full_html=True, div_id=div_id,
                       config={"displayModeBar": False, "staticPlot": True})
    # Die Zellen der Differenzzeile stehen fest im HTML — eine je Balkengruppe,
    # in derselben Reihenfolge wie die Kategorien auf der x-Achse.
    letzte = next(s["differenz"] for s in reversed(schritte) if "differenz" in s)
    zellen = "".join(f"<span>{wert}</span>" for wert in letzte)

    zusatz = SKRIPT.format(
        div_id=div_id, div_id_json=json.dumps(div_id),
        schritte=json.dumps(schritte, ensure_ascii=False),
        anzahl_traces=len(fig.data),
        anzahl_x=len(fig.data[0].x),
        anzahl_annotationen=len(fig.layout.annotations),
        dauer_ms=args.dauer,
        rand_links=RAND_LINKS, rand_rechts=RAND_RECHTS,
        # Die Zeile sitzt im unteren Rand, unterhalb der Achsenbeschriftung.
        zeile_unten=28,
        beschriftung_differenz=TEXTE_ANIMATION["differenz"],
        zellen=zellen)
    html = html.replace("</body>", zusatz + "\n</body>")

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    args.ziel.write_text(html, encoding="utf-8")

    print(f"{len(schritte)} Klickschritte, Kennzahl {args.kennzahl!r}")
    print(f"geschrieben: {args.ziel.relative_to(WURZEL)}")
    print(f"\n  open {args.ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
