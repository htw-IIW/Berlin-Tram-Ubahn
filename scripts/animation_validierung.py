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
from src.analysis.grafiken import validierung_animation         # noqa: E402

from grafik_validierung import werte_fuer                       # noqa: E402

# video/animationen/ — mit -en. Dort liegen die Animationen der
# Videoschnitt-Sitzung (lsa-vorrang, puenktlichkeitsfenster, …), und dieselbe
# Datei zweimal in zwei aehnlich benannten Ordnern ist eine Falle.
STANDARDZIEL = WURZEL / "video" / "animationen" / "validierung_puenktlichkeit.html"

# Der Block wird an das von plotly erzeugte HTML angehaengt. Er haelt nur einen
# Zaehler und schiebt bei jedem Klick den naechsten Schritt in die Figur.
SKRIPT = """
<style>
  html, body {{ margin: 0; padding: 0; background: #ffffff; }}
  #{div_id} {{ width: 100vw; height: 100vh; }}
  #hinweis {{
    position: fixed; right: 18px; bottom: 14px;
    font: 15px/1.4 system-ui, sans-serif; color: #b0bec5;
    pointer-events: none; transition: opacity .4s;
  }}
</style>
<div id="hinweis">Klicken zum Aufbauen · ← zurück</div>
<script>
  (function () {{
    var gd = document.getElementById({div_id_json});
    var schritte = {schritte};
    var stand = 0;

    function zeichnen(bis) {{
      // Immer vom Nullzustand aus neu aufbauen. Das ist ein paar Millisekunden
      // teurer als das reine Vorwaertsschalten, macht aber den Rueckwaertsweg
      // trivial und schliesst aus, dass sich Zustaende aufaddieren.
      var daten = {{}}, layout = {{}};
      for (var i = 0; i < bis; i++) {{
        var s = schritte[i];
        if (s.daten)  Object.assign(daten, s.daten);
        if (s.layout) Object.assign(layout, s.layout);
      }}
      if (Object.keys(daten).length)  Plotly.restyle(gd, daten);
      if (Object.keys(layout).length) Plotly.relayout(gd, layout);
    }}

    function zuruecksetzen() {{
      Plotly.restyle(gd, {{y: [[null, null], [null, null]],
                          text: [["", ""], ["", ""]]}});
      Plotly.relayout(gd, {{"annotations[0].visible": false,
                           "annotations[1].visible": false}});
    }}

    function weiter(richtung) {{
      var neu = Math.min(Math.max(stand + richtung, 0), schritte.length);
      if (neu === stand) return;
      stand = neu;
      zuruecksetzen();
      zeichnen(stand);
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
        e.preventDefault(); stand = 0; zuruecksetzen();
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
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)
    werte = werte_fuer(es, args.monat)

    fig, schritte = validierung_animation(werte, args.kennzahl)

    div_id = "grafik"
    html = fig.to_html(include_plotlyjs=True, full_html=True, div_id=div_id,
                       config={"displayModeBar": False, "staticPlot": True})
    zusatz = SKRIPT.format(div_id=div_id, div_id_json=json.dumps(div_id),
                           schritte=json.dumps(schritte, ensure_ascii=False))
    html = html.replace("</body>", zusatz + "\n</body>")

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    args.ziel.write_text(html, encoding="utf-8")

    print(f"{len(schritte)} Klickschritte, Kennzahl {args.kennzahl!r}")
    print(f"geschrieben: {args.ziel.relative_to(WURZEL)}")
    print(f"\n  open {args.ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
