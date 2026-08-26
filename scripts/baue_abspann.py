#!/usr/bin/env python3
"""Erzeugt video/animationen/abspann.html.

Die Linienführung kommt aus video/animationen/netzplan.json — dieselbe
Quelle wie die Netzvergleichsgrafik, damit der Abspann dasselbe Netz zeigt
wie das Video davor. Das HTW-Logo wird als SVG eingebettet, damit die
Datei ohne Nachbardateien funktioniert.
"""
import json, pathlib, re

WURZEL = pathlib.Path("/Users/valeriamuggironi/Documents/Master/Semester 2/"
                      "NoSQL/Semesterprojekt/Berlin-Tram-UBahn")
QUELLE = WURZEL / "video" / "animationen" / "netzplan.json"
LOGO = WURZEL / "video" / "bild" / "Logo_HTW_Berlin.svg"
ZIEL = WURZEL / "video" / "animationen" / "abspann.html"

NAME = "Valeria Muggironi"

daten = json.loads(QUELLE.read_text())
# Nur was gezeichnet wird: Netz und Linienzüge. Haltestellennamen und die
# Paartabelle des Netzplans braucht der Abspann nicht.
schlank = {
    "farben": daten["meta"]["farben"],
    "linien": [{"netz": l["netz"], "zuege": l["zuege"]} for l in daten["linien"]],
}

# Logo: XML-Deklaration und DOCTYPE raus, damit es inline in HTML steht.
# Die Grössenangaben ebenfalls — die Grösse bestimmt das Stylesheet.
logo = LOGO.read_text()
logo = re.sub(r"<\?xml.*?\?>", "", logo, flags=re.S)
logo = re.sub(r"<!DOCTYPE.*?>", "", logo, flags=re.S)
logo = re.sub(r"<!--.*?-->", "", logo, flags=re.S)
logo = re.sub(r'\s(width|height)="[^"]*"', "", logo, count=2)
logo = logo.strip()

VORLAGE = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <title>Abspann</title>

    <!-- ══════════════════════════════════════════════════════════════
         ABSPANN — was die Animation zeigt

         Beide Netze werden gezeichnet, Tram in Rot und U-Bahn in Blau,
         wie überall im Projekt. Danach treten sie auf ein Viertel ihrer
         Deckkraft zurück und bleiben als Hintergrund stehen; darüber
         erscheinen das HTW-Logo und der Name.

         Kein Selbstlauf: Beim Laden bleibt die Fläche weiss. Erst ein
         Klick oder die Leertaste startet den Ablauf, damit sich der
         Beginn beim Aufnehmen genau setzen lässt.

         Ablauf ab dem Start, Dauer im Stylesheet unter ZEITEN:
           0,0 – 3,0   Linien zeichnen sich
           3,3 – 4,7   Netz tritt auf 25 % zurück
           3,9 – 5,5   Logo und Name blenden ein (überlappend)
           danach      Standbild

         Die Linienführung stammt aus netzplan.json, derselben Quelle wie
         die Netzvergleichsgrafik. Erzeugt von scripts/baue_abspann.py —
         die Daten unten nicht von Hand ändern.

         TASTEN
         Klick / Leertaste / R   starten, später von vorn abspielen

         AUFNEHMEN
         Fenster gross ziehen, Cmd+Shift+5. Die Fläche ist 16:9 und
         skaliert mit dem Fenster; aussen bleibt Weiss wie der
         Hintergrund, es gibt also keine sichtbare Kante.
         ══════════════════════════════════════════════════════════ -->

    <style>
      :root {
        /* ── ZEITEN ─────────────────────────────────────────────── */
        --t-zeichnen: 3s; /* Dauer des Linienaufbaus        */
        --t-zuruecktreten: 1.4s; /* Netz blendet auf 25 % zurück   */
        --t-abspann: 1.6s; /* Logo und Name blenden ein      */

        /* Wie früh der Abspann einsetzt, gemessen am Zurücktreten des
           Netzes. 0,45 heisst: Er beginnt, wenn das Netz nicht ganz zur
           Hälfte verblasst ist. Die Überlappung ist der Grund, warum der
           Übergang weich wirkt statt in zwei Schritten abzulaufen. */
        --ueberlappung: 0.45;

        /* Restdeckkraft des Netzes, wenn der Abspann steht. */
        --netz-rest: 0.25;
      }

      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      html,
      body {
        height: 100%;
        background: #fff;
        overflow: hidden;
        cursor: none;
      }

      body {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue",
          Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
      }

      .buehne {
        position: relative;
        width: 1600px;
        height: 900px;
        flex: none;
        transform-origin: center center;
      }

      #netz {
        position: absolute;
        inset: 0;
        transition: opacity var(--t-zuruecktreten) cubic-bezier(0.4, 0, 0.2, 1);
      }

      /* Vor dem Start ist das Netz nicht nur zurückgezogen, sondern
         unsichtbar. Grund: Bei `stroke-linecap: round` zeichnet der
         Browser für jedes Wegstück der Länge null trotzdem eine runde
         Kappe — als Punkt sichtbar, obwohl die Linie noch gar nicht
         gezeichnet ist. Das Netz ganz auszublenden ist die einzige
         Lösung, die ohne eckige Linienenden auskommt. */
      .buehne.leer #netz {
        visibility: hidden;
      }

      /* Die Linien zeichnen sich, indem die Strichlücke zurückgefahren
         wird. Die Länge setzt das Skript je Pfad einzeln. */
      #netz path {
        fill: none;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      /* Zurückgetretenes Netz. */
      .buehne.zurueck #netz {
        opacity: var(--netz-rest);
      }

      /* ── Abspann ────────────────────────────────────────────────── */
      .abspann {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 54px;

        /* Logo und Name kommen aus einer Spur heran, statt hart
           aufzublenden — dieselbe Bewegung wie in den anderen
           Animationen des Projekts. */
        opacity: 0;
        transform: translateY(18px) scale(0.985);
        transition:
          opacity var(--t-abspann) cubic-bezier(0.4, 0, 0.2, 1),
          transform var(--t-abspann) cubic-bezier(0.22, 0.61, 0.36, 1);
      }
      .buehne.fertig .abspann {
        opacity: 1;
        transform: translateY(0) scale(1);
      }

      /* Weisser Schleier direkt hinter Logo und Name, damit beide auch
         dann ruhig stehen, wenn dort zufällig viele Linien liegen. */
      .abspann::before {
        content: "";
        position: absolute;
        width: 900px;
        height: 460px;
        border-radius: 50%;
        background: radial-gradient(
          ellipse at center,
          rgba(255, 255, 255, 0.96) 0%,
          rgba(255, 255, 255, 0.9) 55%,
          rgba(255, 255, 255, 0) 100%
        );
      }

      .abspann svg {
        position: relative;
        width: 340px;
        height: auto;
      }

      .name {
        position: relative;
        font-size: 46px;
        font-weight: 600;
        color: #000;
        letter-spacing: 0.01em;
      }
    </style>
  </head>

  <body>
    <div class="buehne" id="buehne">
      <svg id="netz" viewBox="0 0 1600 900" aria-hidden="true"></svg>

      <div class="abspann">
        __LOGO__
        <div class="name">__NAME__</div>
      </div>
    </div>

    <script>
      /* DATEN-ANFANG — erzeugt von scripts/baue_abspann.py */
      const DATEN = __DATEN__;
      /* DATEN-ENDE */

      // ── Bühne auf das Fenster skalieren ──────────────────────────────
      const buehne = document.getElementById("buehne");
      function passen() {
        buehne.style.transform =
          "scale(" + Math.min(innerWidth / 1600, innerHeight / 900) + ")";
      }
      addEventListener("resize", passen);
      passen();

      // ── Projektion ───────────────────────────────────────────────────
      // Web-Mercator, danach in das Feld eingepasst — identisch zu
      // netzplan.html, damit beide Animationen dasselbe Netz zeigen.
      const FELD = { x: 90, y: 40, b: 1420, h: 820 };

      const mercX = (lon) => (lon * Math.PI) / 180;
      const mercY = (lat) =>
        Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 180 / 2));

      const alle = DATEN.linien.flatMap((l) => l.zuege.flat());
      const xs = alle.map((p) => mercX(p[1]));
      const ys = alle.map((p) => mercY(p[0]));
      const rand = {
        x0: Math.min(...xs),
        x1: Math.max(...xs),
        y0: Math.min(...ys),
        y1: Math.max(...ys),
      };
      const massstab = Math.min(
        FELD.b / (rand.x1 - rand.x0),
        FELD.h / (rand.y1 - rand.y0),
      );
      const versatzX = FELD.x + (FELD.b - (rand.x1 - rand.x0) * massstab) / 2;
      const versatzY = FELD.y + (FELD.h - (rand.y1 - rand.y0) * massstab) / 2;

      const px = (lat, lon) => [
        versatzX + (mercX(lon) - rand.x0) * massstab,
        // Mercator wächst nach Norden, die SVG-Achse nach Süden.
        versatzY + (rand.y1 - mercY(lat)) * massstab,
      ];

      // ── Netz zeichnen ────────────────────────────────────────────────
      const NS = "http://www.w3.org/2000/svg";
      const netz = document.getElementById("netz");
      const pfade = [];

      // U-Bahn zuerst in den Baum, damit die dünneren Tramlinien an den
      // gemeinsamen Punkten obenauf liegen.
      const sortiert = [...DATEN.linien].sort((a, b) =>
        a.netz === b.netz ? 0 : a.netz === "U-Bahn" ? -1 : 1,
      );

      for (const l of sortiert) {
        for (const zug of l.zuege) {
          if (zug.length < 2) continue;
          const d = zug
            .map((p, i) => (i ? "L" : "M") + px(p[0], p[1]).join(" "))
            .join(" ");
          const pfad = document.createElementNS(NS, "path");
          pfad.setAttribute("d", d);
          pfad.setAttribute("stroke", DATEN.farben[l.netz]);
          pfad.setAttribute("stroke-width", l.netz === "U-Bahn" ? 5 : 3);
          pfad.setAttribute("opacity", l.netz === "U-Bahn" ? 0.9 : 1);
          netz.appendChild(pfad);
          pfade.push(pfad);
        }
      }

      // ── Ablauf ───────────────────────────────────────────────────────
      const stil = getComputedStyle(document.documentElement);
      const sek = (name) => parseFloat(stil.getPropertyValue(name)) * 1000;

      let uhren = [];

      // Ausgangszustand: Netz gezeichnet, aber vollständig zurückgezogen,
      // also eine weisse Fläche. Ohne diesen Schritt stünde beim Laden
      // schon das fertige Netz im Bild.
      function zuruecksetzen() {
        uhren.forEach(clearTimeout);
        uhren = [];
        buehne.classList.remove("zurueck", "fertig");
        buehne.classList.add("leer");
        for (const p of pfade) {
          const laenge = p.getTotalLength();
          p.style.transition = "none";
          p.style.strokeDasharray = laenge;
          p.style.strokeDashoffset = laenge;
        }
      }

      function abspielen() {
        zuruecksetzen();

        // Erzwingt, dass der Ausgangszustand gesetzt ist, bevor die
        // Übergänge eingeschaltet werden.
        netz.getBoundingClientRect();
        buehne.classList.remove("leer");

        // Alle Pfade mit derselben Dauer, damit das Netz gleichmässig
        // entsteht statt Linie für Linie.
        const dauer = sek("--t-zeichnen");
        for (const p of pfade) {
          p.style.transition = `stroke-dashoffset ${dauer}ms ease-in-out`;
          p.style.strokeDashoffset = 0;
        }

        // Der Abspann setzt ein, bevor das Netz fertig verblasst ist —
        // die beiden Bewegungen überlappen, statt aufeinander zu warten.
        const zurueckAb = dauer + 300;
        const abspannAb =
          zurueckAb +
          sek("--t-zuruecktreten") *
            parseFloat(stil.getPropertyValue("--ueberlappung"));

        uhren.push(
          setTimeout(() => buehne.classList.add("zurueck"), zurueckAb),
          setTimeout(() => buehne.classList.add("fertig"), abspannAb),
        );
      }

      addEventListener("keydown", (e) => {
        if (e.code === "Space" || e.key === "r" || e.key === "R") {
          e.preventDefault();
          abspielen();
        }
      });
      addEventListener("click", abspielen);

      // Kein Selbstlauf: Die Fläche bleibt weiss, bis geklickt wird.
      zuruecksetzen();
    </script>
  </body>
</html>
"""

html = (VORLAGE
        .replace("__DATEN__", json.dumps(schlank, ensure_ascii=False,
                                         separators=(",", ":")))
        .replace("__LOGO__", logo)
        .replace("__NAME__", NAME))

ZIEL.write_text(html)
print(f"geschrieben: {ZIEL.relative_to(WURZEL)}  ({len(html):,} Zeichen)")
print(f"Linienzüge: {sum(len(l['zuege']) for l in schlank['linien'])}, "
      f"Linien: {len(schlank['linien'])}")
