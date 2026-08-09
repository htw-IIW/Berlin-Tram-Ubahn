# Codebook — LSA-Status je Haltestelle

Erzeugt von `scripts/export_lsa_haltestellen.py` am 09.08.2026.
Zuordnungsradius: **150 m**.

## Dateien

| Datei | Inhalt |
|---|---|
| `haltestellen_lsa_tram.csv` | eine Zeile je Tram-Haltestelle, 399 Zeilen |
| `lsa_standorte.csv` | eine Zeile je Lichtsignalanlage, 2,307 Zeilen |

Beide lassen sich über `lsa_id` verbinden. `haltestellen_lsa_tram.csv` verbindet
sich über `stop_name` mit `messpunkte_tram_sample.csv`; dort stehen die Spalten
`lsa_status` und `lsa_distanz_m` bereits an jeder Zeile.

## Zuerst: Anlagen sind nicht Haltestellen

Die beiden Ebenen decken sich nicht, und sie zu verwechseln ist die
naheliegendste Fehlerquelle dieser Tabelle:

* Eine Anlage an einer Kreuzung kann **zwei Haltestellen** im Radius haben — bei
  den inaktiven trifft das auf zwei von ihnen zu und erzeugt dort je zwei Zeilen.
* Eine Anlage kann **gar keine** Haltestelle im Radius haben und taucht dann in
  `haltestellen_lsa_tram.csv` überhaupt nicht auf.

Deshalb steht in jeder Tabelle unten, welche Ebene gemeint ist. Für Gruppen-
vergleiche ist **`lsa_id` die Clustervariable**, nicht `stop_name`: Zwei
Haltestellen an derselben Anlage sind keine zwei unabhängigen Beobachtungen.

## Zwei Spalten statt einer Skala

`lsa_status` aus dem Index sieht aus wie eine Rangfolge von `aktiv` bis
`kein_lsa`, mischt aber zwei Fragen mit sehr verschiedener Belegqualität. Der
Export trennt sie deshalb — in denselben drei Kategorien, die auch die Karte in
Notebook 03 färbt:

| Spalte | Frage | Werte | Karte |
|---|---|---|---|
| `lsa_vorhanden` | Liegt eine Anlage an der Haltestelle? **Gemessen.** | `True` / `False` | grün / grau |
| `beeinflussung_belegt` | Ist die Beeinflussung dort in Betrieb? **Nur für M4/M5 beantwortet.** | `inaktiv_belegt`, `nicht_vorhanden_belegt`, `unklar`, `nicht_belegt` | rot |

**Es gibt bewusst keine Spalte `hat_oepnv_beeinflussung`.** Für keine einzige
Anlage ist positiv belegt, dass die Beeinflussung dort arbeitet — der
WFS-Datensatz führt das Feld nicht. `nicht_belegt` heißt genau das: über diese
Anlage sagt keine Quelle etwas. Es heißt nicht "funktioniert".

### Der Rohwert `lsa_status`

Bleibt für den Abgleich mit Notebook 03 in der Datei:

| Wert | Bedeutung | Quelle |
|---|---|---|
| `aktiv` | Anlage im Radius, **nicht** in der Ausnahmeliste | keine — siehe unten |
| `inaktiv` | Beeinflussung vorhanden, aber nicht in Betrieb | Drucksache 19/19804 |
| `nicht_vorhanden` | keine Beeinflussung eingebaut | Drucksache 19/19804 |
| `unklar` | Zuordnung der Quelle nicht eindeutig (Alexanderstraße) | — |
| `kein_lsa` | keine Anlage innerhalb von 150 m | — |
| `kein_tram` | nächste Anlage ist als "ohne Tramstrecke" geführt | — |

Verteilung auf beiden Ebenen:

| Status | Anlagen im Index | davon einer Halte zugeordnet | Haltestellen |
|---|---|---|---|
| `aktiv` | 307 | 237 | 254 |
| `kein_lsa` | 0 | 0 | 135 |
| `inaktiv` | 6 | 5 | 7 |
| `kein_tram` | 1987 | 2 | 2 |
| `unklar` | 7 | 1 | 1 |

Die erste Spalte zählt alle Anlagen Berlins, die zweite nur die mit einer
Tram-Haltestelle im 150-m-Radius, die dritte die Haltestellen. Von den
307 als `aktiv` geführten Anlagen liegen also
237 an einer Haltestelle; sie versorgen
254 Halte.

Zwei Eigenheiten der Tabelle:

* **`nicht_vorhanden` kommt nicht vor.** Die einzige Anlage dieser Kategorie ist
  durch Korrektur 1 auf `unklar` gegangen (siehe unten). Der Wert bleibt hier
  beschrieben, weil er im Rohindex existiert.
* **`kein_tram` bei einer Tram-Haltestelle ist ein Widerspruch** und trifft
  2 Halte. Der Status wurde beim Seed über die Nähe zu einer
  Haltestelle des `tram-stops`-Index vergeben, die Koordinaten hier stammen aus
  dem Abfahrtsindex — knapp außerhalb des Radius bei der einen Rechnung, knapp
  innerhalb bei der anderen. Wie `kein_lsa` zu behandeln.

## Der entscheidende Vorbehalt — woher `aktiv` kommt

Der WFS-Datensatz der Senatsverwaltung enthält Koordinaten und Bezeichnungen
aller Berliner Anlagen, aber **keine Angabe darüber, ob die ÖPNV-Beeinflussung
in Betrieb ist**. Der Status entsteht in zwei Schritten im Collector:

1. `src/collector/seed_lsa.py` — alle 2,307 Anlagen starten auf `unbekannt`.
   Nur wer mit der Bezeichnung auf eine **hartcodierte Liste aus der Drucksache**
   passt, bekommt `inaktiv` oder `nicht_vorhanden`. Das sind 11 Einträge.
2. `src/collector/enrich_lsa_tram.py` — jede verbliebene `unbekannt`-Anlage
   **innerhalb von 150 m einer Tram-Haltestelle** wird auf `aktiv` gesetzt,
   der Rest auf `kein_tram`.

`aktiv` heißt damit wörtlich: *liegt in der Nähe einer Haltestelle und stand
nicht auf der Liste.* Über die Beeinflussung sagt es **nichts**. Die 307
`aktiv`-Anlagen sind schlicht die Anlagen am Tramnetz.

Belegt ist ausschließlich die negative Seite: Die Drucksache 19/19804 (Antwort
des Senats vom 07.08.2024) deckt **allein die Linien M4 und M5** ab und nennt
dort sieben Anlagen — eine ohne Beeinflussung, sechs mit vorhandener, aber nicht
in Betrieb befindlicher.

Wer daraus einen Effekt schätzt, schätzt den Effekt einer Klassifikation, deren
positive Kategorie ungeprüft ist. Die Gruppen sind zudem sehr ungleich besetzt
(254 gegen 7 Halte) — ein Gruppenvergleich hängt an einer Handvoll
Haltestellen und sollte auf Haltestellenebene gerechnet werden, nicht auf
Einzelabfahrten. Auf Abfahrtsebene erzeugen 100.000 Beobachtungen aus 400
Haltestellen einen p-Wert, der die Zahl der Haltestellen und nicht die der
Abfahrten widerspiegelt (Notebook 03, Abschnitt 4e: Designeffekt Median 2,1).

### Die Vergleichsgruppe: M4 und M5, nicht das ganze Netz

Weil die Drucksache nur diese beiden Linien geprüft hat, steckt in einem
Vergleich der belegt-inaktiven Halte gegen **alle** Halte auch die Frage, welche
Linien überhaupt untersucht wurden. Die Spalte `auf_drucksachen_linie` grenzt auf
die geprüfte Ebene ein — und der Abstand schrumpft dabei:

| Gruppe | alle Linien | nur M4/M5 |
|---|---|---|
| `aktiv` | +1.2 s (242 Halte) | +2.1 s (71 Halte) |
| `inaktiv` | +6.3 s (6 Halte) | +6.3 s (6 Halte) |
| `kein_lsa` | +1.1 s (114 Halte) | +1.3 s (25 Halte) |

### Begriff

Der Senat schreibt durchgehend **„ÖPNV-Beeinflussung"** und nicht „Vorrang" — ein
absoluter Vorrang sei im Stadtverkehr wegen der Zielkonflikte meist nicht
möglich. Diese Auswertung übernimmt den Begriff; „Vorrang" kommt in den
Spaltennamen nicht vor.

## Zwei Korrekturen gegen die Primärquelle

Vorgenommen in der Auswertung, nicht im Index, damit die Abweichung sichtbar und
die Korrektur umkehrbar bleibt (`src/analysis/lsa.py`):

1. **Alexanderstraße.** Der Index führt sieben Anlagen als `nicht_vorhanden`; die
   Drucksache nennt genau eine. Der Seed hat offenbar auf den Straßennamen
   gemustert — ausgerechnet die Anlage, die dem Namen wörtlich entspricht,
   steht im Index als `aktiv`. Die sieben stehen jetzt auf `unklar`.
2. **Zwei fehlende Anlagen nachgetragen** — Antonplatz und Berliner
   Allee/Buschallee, beide laut Drucksache inaktiv, im Index nicht vorhanden.
   Erkennbar an `lsa_id` mit Präfix `drs-19804-`.

## Spalten — `haltestellen_lsa_tram.csv`

| Spalte | Bedeutung |
|---|---|
| `stop_name`, `stop_id` | Haltestelle |
| `lat`, `lon` | Koordinaten aus dem Abfahrtsindex |
| `linien` | alle Linien, die hier halten, mit `;` getrennt |
| `lsa_vorhanden` | **Frage 1:** Anlage im 150-m-Radius. Gemessen |
| `beeinflussung_belegt` | **Frage 2:** `inaktiv_belegt`, `nicht_vorhanden_belegt`, `unklar`, `nicht_belegt` |
| `auf_drucksachen_linie` | Halt liegt an M4 oder M5 — nur dort hat die Quelle nachgesehen |
| `lsa_status` | Rohwert des Index, siehe oben |
| `lsa_distanz_m` | Entfernung zur nächsten Anlage im Radius |
| `lsa_im_radius` | Zahl der Anlagen im Radius. Zugeordnet wird die **nächste**, nicht die schlechteste |
| `lsa_id`, `lsa_bezeichnung` | die zugeordnete Anlage |
| `lsa_bemerkung` | Begründung aus der Drucksache, warum keine Beeinflussung wirkt — nur bei `inaktiv` / `nicht_vorhanden` gefüllt |
| `avg_delay_s` | mittlere Verspätung an dieser Haltestelle, gesamter Erhebungszeitraum |
| `erzeugte_verspaetung_s` | mittleres `delta_delay` **im Zulauf** auf diese Haltestelle, 60 Werktage |
| `n_segmentbeobachtungen` | Beobachtungen hinter `erzeugte_verspaetung_s` |
| `n_abfahrten`, `n_mit_delay` | Umfang der Verspätungsdaten |
| `ist_betriebshalt` | Betriebshof, `[Ausstieg]`, `[Endstelle]` — **vor der Auswertung ausschließen** |

`erzeugte_verspaetung_s` ist die Größe, die für einen LSA-Vergleich taugt, nicht
`avg_delay_s`: Die Verspätung an einer Haltestelle ist überwiegend geerbt und
misst vor allem die Position in der Linie. Die Differenz zum vorherigen Halt ist
um diesen Upstream-Effekt bereinigt.

Mittelwerte je Status, ohne Betriebshalte:

| Status | Halte | Ø Verspätung (s) | Ø erzeugte Verspätung (s) |
|---|---|---|---|
| `aktiv` | 249.0 | +32.0 | +1.23 |
| `inaktiv` | 7.0 | +41.4 | +6.31 |
| `kein_lsa` | 129.0 | +17.9 | +1.13 |
| `kein_tram` | 2.0 | +15.4 | +0.85 |
| `unklar` | 1.0 | +21.8 | -1.14 |

## Die 6 inaktiven Anlagen im Klartext — und warum das die Auswertung entscheidet

Die Drucksache 19/19804 nennt **6 Anlagen** mit vorhandener, aber nicht in
Betrieb befindlicher Beeinflussung. 5 davon haben eine Haltestelle im
150-m-Radius; sie erzeugen die folgenden **7 Zeilen** der
Haltestellentabelle:

| Anlage | Haltestelle | Begründung laut Drucksache | Ø erzeugte Verspätung (s) |
|---|---|---|---|
| Landsberger Al. / Karl-Lade-Str. - Oderbruchstr. | Karl-Lade-Str. (Berlin) | Langsamfahrstelle wegen Gleisschäden | +15.2 |
| Landsberger Al. / Karl-Lade-Str. - Oderbruchstr. | Oderbruchstr. (Berlin) | Langsamfahrstelle wegen Gleisschäden | +12.1 |
| Falkenberger Ch. / Welsestr. | Welsestr. (Berlin) | Langsamfahrstelle wegen Gleisschäden | +6.1 |
| Antonplatz | Antonplatz (Berlin) | neue Software nach Knotenumbau in Projektierung | +5.4 |
| Greifswalder Str. / Michelangelostr. - Ostseestr. | Greifswalder Str./Ostseestr. (Berlin) | Kein stabiler Betrieb wegen veralteter Hardware, Modernisierung in Planung | +5.2 |
| Berliner Allee / Buschallee | Buschallee (Berlin) | Bauzustand Berliner Wasserbetriebe | -6.1 |
| Falkenberger Ch. / Welsestr. | Falkenberg (Berlin) | Langsamfahrstelle wegen Gleisschäden |  |

Ohne Haltestelle im Radius, deshalb nicht in der Tabelle:

* **Suermondtstr. - Hauptstr. / Seefelder Str. / Konrad-Wolf-Str.** — Nach Hardware-Modernisierung Software in Anpassung

**2 der 6 Anlagen sind wegen einer Langsamfahrstelle nach
Gleisschäden außer Betrieb** — sie stehen an 4 der 7 Haltestellen und
liefern die beiden höchsten Werte der Tabelle. Damit ist die naheliegende Lesart
nicht die einzige:

* *Kausal:* Die Beeinflussung fehlt, die Bahn steht länger an der Ampel.
* *Konfundiert:* Der Gleisschaden verlangsamt die Bahn **und** ist der Grund,
  warum die Anlage abgeschaltet wurde. Die Ampel ist dann Symptom, nicht Ursache.

Die Drucksache belegt den zweiten Mechanismus selbst. In Antwort 7 schreibt der
Senat, bei *„Langsamfahrstellen durch die BVG aufgrund von Gleisschäden"*
übersteige der Projektierungsaufwand die Dauer der Einschränkung, deshalb werde
vorübergehend auf Festzeitprogramme umgestellt. Die Behörde sagt also selbst,
dass das Gleis zuerst kommt und die Ampel danach.

Aus diesen Daten lässt sich zwischen beiden Lesarten nicht entscheiden. Die Spalte
`lsa_bemerkung` ist deshalb keine Fußnote, sondern die Kontrollvariable — und die
Größenordnung, um die es geht, ist klein: Wer den Gleisschadensfall herausrechnet,
behält 3 Anlagen an 3 Haltestellen. Das
ist zu wenig für eine belastbare Schätzung, aber ehrlicher als der Gesamtwert.

**Auf dieser Gruppengröße hängt jeder Test an einzelnen Anlagen.** Die beiden
höchsten Werte der Tabelle — Karl-Lade-Str. und Oderbruchstr. — gehören zu
**derselben** Anlage an der Landsberger Allee. Als zwei unabhängige Beobachtungen
gezählt, verdoppeln sie den Befund, den sie belegen sollen.

Ein Nebenbefund aus Notebook 03 stützt die Konfundierungslesart: Der Unterschied
ist über die Tageszeit **flach** (Hauptverkehrszeit, Nebenzeit und Nacht alle
r ≈ 0,47). Eine Beeinflussungsanlage kann nachts kaum wirken, wenn kaum Verkehr
da ist — ein Gleisschaden wirkt rund um die Uhr.

## Spalten — `lsa_standorte.csv`

| Spalte | Bedeutung |
|---|---|
| `lsa_id` | aus den Koordinaten abgeleitete ID; `drs-19804-*` bei den Nachträgen |
| `bezeichnung` | Ortsangabe. **`standort` ist im Index durchgängig leer** |
| `lat`, `lon` | Koordinaten |
| `oepnv_status` | siehe oben, mit Korrekturen |
| `oepnv_bemerkung` | Begründung aus der Drucksache |
| `tram_linien` | Tramlinien im 150-m-Umkreis, beim Seed abgeleitet |
