# Codebook — Stichprobenexport für die externe Regressionsanalyse

Erzeugt von `scripts/export_regression_sample.py` am 09.08.2026.
Netz: **tram**, Index `tram-departures-v2`.

## Dateien

| Datei | Inhalt |
|---|---|
| `messpunkte_tram_sample.csv` | eine Zeile je Abfahrt (Messpunkt), 121,026 Zeilen |
| `segmente_tram_mittelwerte.csv` | mittlere erzeugte Verspätung je Haltestellenpaar, Grundgesamtheit |

## Stichprobendesign

Geschichtete Zufallsstichprobe **auf Fahrtebene**, Schicht = Erhebungstag x Stunde.

| | |
|---|---|
| Analysefenster | 2026-04-27 bis 2026-07-29, nur Werktage |
| Ausgeschlossen | Collector-Ausfall 2026-06-27 bis 2026-07-08, Teiltage, Linie 88 (Fremdbetrieb) |
| Erhebungstage | 60 |
| Schichten | 60 x 24 = 1,440 |
| Fahrten je Schicht (Soll) | 3 |
| Gezogene Fahrten | 4,297 |
| Halte (Zeilen) | 121,026 |
| davon mit Echtzeitwert | 90.7% |
| Zufallsseed | 20260809 |

Gezogen wird die **Fahrt**, nicht der einzelne Halt: Die erzeugte Verspätung
zwischen zwei Haltestellen ist eine Differenz innerhalb einer Fahrt und lässt
sich aus unabhängig gezogenen Einzelabfahrten nicht bilden. Von jeder gezogenen
Fahrt sind **alle** Halte enthalten, auch die ohne Echtzeitwert.

Die Schicht bezieht sich auf die Abfahrt, über die die Fahrt in die Stichprobe
kam. Eine Fahrt läuft über eine Stundengrenze hinweg, deshalb ist die
Stundenverteilung der **Zeilen** nur annähernd, nicht exakt gleichmäßig:

```
00h 5,256  01h 3,993  02h 4,397  03h 4,122  04h 4,695  05h 4,718  06h 5,234  07h 4,923  08h 5,112  09h 5,418  10h 5,407  11h 4,981  12h 5,404  13h 5,311  14h 4,856  15h 5,201  16h 5,262  17h 5,023  18h 5,247  19h 5,280  20h 5,288  21h 5,426  22h 5,417  23h 5,055
```

### Gewichtung

Das Design ist über Stunden **balanciert**, nicht proportional: Nachtstunden
sind gegenüber ihrem tatsächlichen Verkehrsaufkommen stark überrepräsentiert.

* Für **Regressionen**, die die Uhrzeit als Regressor führen, ist das gewollt
  und die Spalte `gewicht` wird nicht gebraucht — die Schichtvariable steht im
  Modell.
* Für **deskriptive Mittelwerte über den ganzen Tag** muss mit `gewicht`
  gewichtet werden, sonst zieht der Nachtverkehr das Ergebnis.

`gewicht` = Zahl der Fahrten in der Schicht / Zahl der daraus gezogenen Fahrten.
Näherung: Die Schichtgröße stammt aus einer `cardinality`-Aggregation
(HyperLogLog++, bei diesen Größenordnungen praktisch exakt), und eine Fahrt, die
zwei Stunden überspannt, hätte in beiden Schichten gezogen werden können.

## Spalten

### Das JSON-Dokument, Feld für Feld

| Spalte | Typ | Bedeutung |
|---|---|---|
| `doc_id` | text | Elasticsearch `_id`: `trip_id-stop_id-planned_when` |
| `trip_id` | text | BVG-Fahrt-ID. Enthält das Datum, ist also nicht tagesübergreifend |
| `collected_at` | ISO-8601 (UTC) | Zeitpunkt der letzten Erfassung dieser Abfahrt |
| `planned_when` | ISO-8601 (+02:00) | Fahrplanmäßige Abfahrt |
| `when` | ISO-8601 (+02:00) | Prognostizierte/tatsächliche Abfahrt, leer ohne Echtzeitdaten |
| `delay_s` | ganze Zahl | Verspätung in Sekunden, negativ = zu früh |
| `cancelled` | bool | Fahrt ausgefallen |
| `line_name` | text | Linie, z. B. `M2` |
| `line_id` | text | interne VBB-Linien-ID |
| `direction` | text | Fahrtziel (Endhaltestelle) |
| `stop_id` | text | BVG-Haltestellen-ID |
| `stop_name` | text | Haltestellenname |
| `stop_lat`, `stop_lon` | Dezimalgrad | aus dem `geo_point`-Objekt `stop_location` aufgetrennt |
| `stop_sequence` | — | im Index durchgängig leer (die API liefert es nicht) |
| `hour_of_day` | 0–23 | aus `planned_when` abgeleitet, im Index gespeichert |
| `day_of_week` | 0–6 | 0 = Montag |
| `is_weekend` | bool | fast durchgängig `False` (nur Werktage); `True` nur für die Halte einer Freitagnacht-Fahrt nach Mitternacht |

### Abgeleitete Zeitangaben

| Spalte | Bedeutung |
|---|---|
| `datum` | Kalendertag der planmäßigen Abfahrt, Ortszeit Berlin |
| `uhrzeit` | `HH:MM` der planmäßigen Abfahrt, Ortszeit |
| `minute_im_tag` | 0–1439, für stetige Tageszeitverläufe (Splines, Fourier-Terme) |

`datum` weicht bei Fahrten über Mitternacht vom `stratum_datum` ab: Gezogen wird
die Fahrt über eine ihrer Abfahrten, enthalten sind alle ihre Halte — auch die
jenseits des Datumswechsels. Die Zahl der Kalendertage in der Datei ist deshalb
um eins höher als die Zahl der Erhebungstage.

### Erzeugte Verspätung zwischen den Haltestellen

| Spalte | Bedeutung |
|---|---|
| `halt_index` | Position dieses Halts in der Fahrt, 1 = erster erfasster Halt |
| `n_halte_fahrt` | Zahl der erfassten Halte dieser Fahrt |
| `stop_from` | vorhergehender Halt **mit Echtzeitwert** derselben Fahrt |
| `stop_from_id` | dessen `stop_id` |
| `delay_vorher_s` | `delay_s` an `stop_from` |
| `delta_delay_s` | **`delay_s` − `delay_vorher_s`** — die auf dem Abschnitt `stop_from` → `stop_name` erzeugte Verspätung |
| `delta_plausibel` | `False`, wenn \|`delta_delay_s`\| > 600 s |
| `segment_mittel_delta_s` | Mittel von `delta_delay_s` für dieses Haltestellenpaar über den **gesamten** Erhebungszeitraum |
| `segment_std_delta_s` | dessen Standardabweichung |
| `segment_n` | Zahl der Beobachtungen, auf denen der Mittelwert beruht |

`delta_delay_s` ist die eigentlich auswertbare Größe. Die Verspätung an einer
Haltestelle ist überwiegend **geerbt** — eine Fahrt, die spät im Linienverlauf
steht, ist verspätet, unabhängig davon, was an dieser Haltestelle geschieht. Wer
Haltestellen nach mittlerer `delay_s` sortiert, misst deshalb vor allem die
Position in der Linie. Die Differenz ist um diesen Upstream-Effekt bereinigt.

Zwei Fallstricke:

1. **`delta_delay_s` ist minutenquantisiert.** Alle `delay_s`-Werte sind exakte
   Vielfache von 60 — die BVG-API meldet ganze Minuten, die Sekundenangabe ist
   eine Umrechnung, keine Messung. Differenzen springen deshalb in
   60-s-Schritten. Mittelwerte über viele Beobachtungen bleiben präzise (die
   Rundung trägt rund 17,3/√n Sekunden zum Standardfehler bei), Mediane
   einzelner Abfahrten liegen fast immer auf 0.
2. **Pseudo-Abschnitte.** Fehlt ein Zwischenhalt in der Erfassung, verbindet
   `stop_from` → `stop_name` zwei echte Abschnitte und weist deren Verspätung
   zusammen aus. Solche Paare sind selten und erkennbar an kleinem `segment_n`;
   die Analysen in diesem Projekt filtern auf `segment_n >= 2,000`
   (das lässt 763 von 5.724 Paaren übrig, deckt aber 98,8 % aller Beobachtungen ab).
   Fahrten mit weniger als 3 Halten erlauben keine sinnvolle
   Differenzbildung.

### Qualitätsmerker

| Spalte | Bedeutung |
|---|---|
| `hat_echtzeit` | `delay_s` vorhanden. Fehlende Echtzeitdaten sind vermutlich **nicht** zufällig verteilt |
| `ist_betriebshalt` | Betriebshof, `[Ausstieg]`, `[Endstelle]` — dort steht das Fahrzeug planmäßig länger, die „Verspätung" erlebt kein Fahrgast. **Vor der Auswertung ausschließen.** |

Eckige Klammern im Haltestellennamen sind für sich **kein** Ausschlussgrund:
Die meisten unterscheiden nur Bahnsteige derselben Haltestelle
(`U Alexanderplatz (Berlin) [Tram]`) und sind reguläre Halte.

### Stichprobendesign

| Spalte | Bedeutung |
|---|---|
| `stratum_datum`, `stratum_stunde` | Schicht, über die die Fahrt gezogen wurde |
| `stratum_n_fahrten` | Zahl der Fahrten in dieser Schicht (Grundgesamtheit) |
| `stratum_n_gezogen` | Zahl der daraus gezogenen Fahrten |
| `gewicht` | `stratum_n_fahrten / stratum_n_gezogen` |

## Was diese Daten nicht hergeben

* **Keine Jahresaussagen.** Erhoben wurde vom 27.04. an, also Frühjahr und
  Sommer — rund ein Viertel des Jahres. Vereisung, Laubfall und Schneeräumung
  liegen außerhalb des Fensters und treffen ausschließlich die Tram.
* **Keine Zeittrends über den 08.07.2026 hinweg.** Die Echtzeitabdeckung springt
  an diesem Tag in beiden Netzen deutlich nach oben (Tram 81 % → 96 %). Ein
  Anstieg der gemessenen Verspätung über diese Grenze hinweg kann allein aus der
  veränderten Erfassung stammen. Querschnittsvergleiche über das ganze Fenster
  sind zulässig.
* **`cancelled` ist nach dem 08.07. für die U-Bahn unbrauchbar** (Quote fällt von
  1,16 % auf 0,06 %, mehrere Tage mit exakt null Ausfällen bei ~76.000
  Abfahrten). Die Tram macht den Bruch nicht mit.

Vollständig in `DATASET.md`, Abschnitt *Known Data Characteristics*.
