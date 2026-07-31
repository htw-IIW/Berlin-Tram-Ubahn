# Kibana-Visualisierungen — Schritt für Schritt

Für Kibana **8.17.2**. Jede Grafik ist einer Aussage aus dem Video zugeordnet.

**Zugang:** http://tram-pi:5601 — Login `elastic` / `changeme`
(lokal: http://localhost:5601)

---

## Schritt 0 — Vorbereitung (einmalig, ~5 Minuten)

### 0.1 Gemeinsame Data View über beide Netze

Die vorhandenen Data Views decken je ein Netz ab. Für jeden Vergleich brauchst du eine,
die beide enthält.

1. Links im Menü **☰ → Management → Stack Management**
2. **Kibana → Data Views**
3. Button **Create data view** (oben rechts)
4. Ausfüllen:
   - **Name:** `Abfahrten beide Netze`
   - **Index pattern:** `*-departures-v2`
     → rechts muss erscheinen: *Your index pattern matches 2 sources*
   - **Timestamp field:** `collected_at`
5. **Save data view to Kibana**

### 0.2 Dunkles Design einschalten

1. **Stack Management → Advanced Settings**
2. Nach `theme:darkMode` suchen → auf **Dark** stellen
3. Unten **Save changes**, danach Seite neu laden

> Passt zu den rbb24-Grafiken und blendet im Video nicht.

### 0.3 Die Filter, die überall gelten

**Ohne diese Filter zeigt Kibana andere Zahlen als deine Notebooks** — dann
widerspricht sich dein Video selbst. Herleitung in `notebooks/01_eda.ipynb`,
Abschnitt 2b.

Diesen Text in jede Visualisierung in die **Suchleiste oben** einfügen:

```
delay_s: * and not stop_name: ("Betriebshof*" or "*[Ausstieg]" or "*[Endstelle]")
```

**Zeitraum** oben rechts einstellen: *Absolute* → `27. Apr 2026 00:00` bis
`29. Jul 2026 23:59`.

> **Tipp:** Einmal eingeben, dann in der Suchleiste auf **Save** → *Save current query*
> unter dem Namen `Basisfilter`. Danach lädst du ihn in jeder neuen Visualisierung mit
> zwei Klicks.

---

## Grafik 1 — Die vier Kernzahlen *(Video, Szene 4 und 5)*

**Belegt die Aussage:** „Fast jede dritte Tram-Abfahrt liegt außerhalb des
Pünktlichkeitsfensters — bei der U-Bahn jede zehnte."

Große Zahlen sind im Video besser lesbar als jedes Diagramm. Diese vier Kacheln sind
der stärkste Beleg im ganzen Set.

### Anlegen

1. **☰ → Analytics → Dashboard → Create dashboard**
2. **Create visualization** → oben links Data View auf **`Abfahrten beide Netze`**
3. Rechts oben Diagrammtyp auf **Metric** stellen
4. Basisfilter in die Suchleiste einfügen (siehe 0.3)
5. Im rechten Panel bei **Primary metric** auf das Feld klicken
6. Unten auf **Formula** wechseln und einfügen:

```
count(kql='delay_s <= -60') / count()
```

7. Darunter bei **Value format** → **Percent**, Dezimalstellen **1**
8. Bei **Breakdown by** → **Top values of** → Feld `_index`, Größe **2**
9. **Save and return**

Ergebnis: zwei Kacheln nebeneinander, eine je Netz — Tram rund **19 %**, U-Bahn rund
**6 %** zu früh.

### Die zweite Kachel

Dieselben Schritte, aber die Formel:

```
count(kql='delay_s >= 180') / count()
```

Ergebnis: Tram rund **11 %**, U-Bahn rund **4 %** zu spät.

### Optional: das Pünktlichkeitsfenster als eine Zahl

```
1 - count(kql='delay_s > -60 and delay_s < 180') / count()
```

Ergebnis: Tram rund **30 %**, U-Bahn rund **10 %** außerhalb des Fensters.

> **Fürs Video:** Diese eine Zahl trägt Szene 4. Nimm sie groß auf, ohne Diagramm
> drumherum.

---

## Grafik 2 — Der Abstand wächst mit der Schwere *(Video, Szene 4)*

**Belegt die Aussage:** „Beim Durchschnitt ist der Unterschied klein, bei der
Zuverlässigkeit groß."

Das ist der Kern deiner Argumentation — und in Kibana überraschend gut darstellbar.

1. Im Dashboard **Create visualization**, Data View `Abfahrten beide Netze`
2. Diagrammtyp: **Bar vertical** (gruppiert, nicht gestapelt)
3. Basisfilter einfügen
4. **Horizontal axis** → **Filters** wählen. Fünf Filter anlegen, jeweils mit Label:

| KQL | Label |
|---|---|
| `delay_s >= 60` | ab 1 Min |
| `delay_s >= 120` | ab 2 Min |
| `delay_s >= 180` | ab 3 Min |
| `delay_s >= 300` | ab 5 Min |
| `delay_s >= 600` | ab 10 Min |

5. **Vertical axis** → **Formula**:

```
count() / overall_sum(count())
```

> **Achtung, hier ist eine Falle.** Diese Formel normiert über das gesamte Diagramm,
> nicht je Netz. Weil die Tram fast doppelt so viele Abfahrten hat, wäre der Vergleich
> verzerrt.
>
> **Lösung:** Baue die Grafik **zweimal**, je einmal mit dem Zusatzfilter
> `_index: "tram-departures-v2"` bzw. `_index: "ubahn-departures-v2"`, und lege beide
> im Dashboard nebeneinander. Beide Diagramme dann auf **dieselbe Y-Achsenskala**
> setzen (rechtes Panel → *Left axis* → *Bounds* → Max fest auf `0.4`).

6. **Breakdown by** leer lassen (die Trennung macht der Filter)
7. Achsenbeschriftung: *Anteil der Abfahrten*, Format **Percent**
8. **Save and return**

Erwartetes Bild: Bei „ab 1 Min" liegen die Balken fast gleich hoch, bei „ab 10 Min"
ist der Tram-Balken um ein Vielfaches höher. **Genau das ist die Aussage.**

---

## Grafik 3 — Die Verspätungskarte *(Video, Szene 6)*

**Belegt die Aussage:** „Das Problem ist nicht das System, sondern der Ort."

Das ist die Visualisierung, für die sich Kibana wirklich lohnt — sie nutzt das
`geo_point`-Mapping, das eine reine Python-Auswertung so nicht hergibt. Zugleich der
beste Beleg für den NoSQL-Teil der Abgabe.

1. **☰ → Analytics → Maps → Create map**
2. **Add layer** (rechts) → **Clusters**
3. **Data view:** `Straßenbahn Abfahrten`
4. **Geospatial field:** `stop_location`
5. Unter **Metrics** → **Add metric**:
   - Aggregation: **Average**
   - Field: `delay_s`
6. Unter **Layer style**:
   - **Fill color** → *By value* → Metrik **Average of delay_s**
   - Farbskala **Yellow to Red**
   - **Custom range** setzen: Min `0`, Max `90`
   - **Symbol size** → *By value* → **Count of documents**
7. Oben in die Suchleiste den Basisfilter einfügen
8. Zeitraum oben rechts setzen
9. Karte auf das Tram-Netz zoomen (Osten Berlins)
10. **Save**

> **Kachelgröße:** Bei zu grober Auflösung verschwinden die Hotspots im Mittelwert.
> Zoome so weit hinein, dass einzelne Haltestellen unterscheidbar sind — die
> Landsberger Allee muss als roter Korridor erkennbar sein.

> **Alternative mit mehr Aussagekraft:** Statt der mittleren Verspätung den Anteil über
> 180 s. Dafür bei der Metrik **Count** wählen und in die Suchleiste zusätzlich
> `delay_s >= 180` schreiben. Dann zeigen die Farben, wo *häufig* stark verspätet wird,
> nicht wo der Mittelwert hoch ist — das passt besser zu deiner Argumentation.

---

## Grafik 4 — Störungsarten im Netzvergleich *(Video, Szene 8)*

**Belegt die Aussage:** „19 wetterbedingte Meldungen bei der Tram, bei der U-Bahn
keine."

1. Neue Data View anlegen (wie in 0.1): Index pattern `*-disruptions`,
   Name `Störungen beide Netze`, **Timestamp field: `valid_from`**
2. **Create visualization** → Diagrammtyp **Bar horizontal**
3. **Vertical axis** → **Top values of** `summary.keyword`, Größe **10**
4. **Horizontal axis** → **Unique count of** `valid_from`
5. **Breakdown by** → **Top values of** `_index`, Größe 2
6. In die Suchleiste:

```
not text: "Test - Please ignore*"
```

> **Das ist die wichtigste Einstellung der ganzen Grafik.** Nimm als Metrik **niemals
> *Count of records***. Eine Störung erzeugt ein Dokument je betroffener Fahrt **und**
> Haltestelle — eine dreiwöchige Baustelle allein erzeugt Hunderttausende und
> dominiert dann das gesamte Bild. *Unique count of `valid_from`* nähert die Zahl der
> tatsächlichen Vorfälle an. Begründung in `DATASET.md`, Punkt 7.
>
> Der Testmeldungs-Filter entfernt erfundene BVG-Meldungen — darunter ausgerechnet die
> einzige wetterbezogene U-Bahn-Meldung im gesamten Zeitraum (`DATASET.md`, Punkt 8).

Erwartetes Bild: Bei der U-Bahn dominieren defekte Aufzüge (rund 86 % der Vorfälle),
bei der Tram Betriebsunterbrechungen und Umleitungen.

---

## Grafik 5 — Der Erfassungsbruch *(nicht fürs Video, für die Fragerunde)*

**Belegt die Aussage:** „Ich habe geprüft, ob die Daten plausibel sind."

Der schlagendste Beleg dafür, dass die Datenqualität untersucht wurde.

1. **Create visualization** → **Line**, Data View `Abfahrten beide Netze`
2. **Horizontal axis** → `collected_at`, **Minimum interval: 1 day**
3. **Vertical axis** → **Formula**:

```
count(kql='cancelled: true') / count()
```

4. **Breakdown by** → `_index`
5. Zeitraum: gesamter Erhebungszeitraum, **ohne** Ausfallfilter
6. Value format: **Percent**

Man sieht die U-Bahn-Kurve am 8. Juli von rund 1 % auf nahezu null einbrechen, während
die Tram-Kurve unverändert weiterläuft. Genau daraus folgt die Regel, Ausfallquoten nur
bis zum 26. Juni zu vergleichen.

---

## Screenshots aufnehmen

- Browserfenster auf **1920 × 1080** ziehen
- Panel-Menü (**⋯** oben rechts am Panel) → **Maximize panel**, dann nur das Panel
  aufnehmen
- `Cmd+Shift+4`, dann **Leertaste**, dann auf das Panel klicken — nimmt genau ein
  Fenster ohne Menüleiste auf
- **Schriftgrößen prüfen:** Was am Monitor lesbar ist, ist im Video oft zu klein.
  Notfalls den Browser mit `Cmd +` auf 125 % zoomen und dann aufnehmen.
- Panel-Titel so formulieren, dass er ohne Erklärung verständlich ist

---

## Farben durchhalten

Damit Kibana, Notebooks und rbb24-Grafiken zusammen wirken:

| | Farbe |
|---|---|
| Tram | `#E53935` (rot) |
| U-Bahn | `#1E88E5` (blau) |
| neutral / Hintergrund | `#90A4AE` (grau) |

In Lens: rechtes Panel → Serie anklicken → **Color** → Hex eingeben.

---

## Kontrolle: stimmen deine Kacheln?

Vergleiche die Werte aus Grafik 1 mit diesen Richtwerten. Sie stammen aus den Notebooks
über denselben Zeitraum.

| | zu früh (≤ −60 s) | zu spät (≥ 180 s) | außerhalb des Fensters |
|---|---|---|---|
| **Tram** | ~19 % | ~11 % | ~30 % |
| **U-Bahn** | ~6 % | ~4 % | ~10 % |

**Weichen deine Zahlen deutlich ab, prüfe in dieser Reihenfolge:**

1. **Zeitraum** oben rechts — steht er auf 27.04. bis 29.07.2026?
2. **Basisfilter** — ist `delay_s: *` gesetzt? Ohne diesen Teil zählt Kibana auch
   Abfahrten ohne Echtzeitdaten mit und alle Anteile fallen zu niedrig aus.
3. **Data View** — liegt die richtige an? `Abfahrten beide Netze` muss zwei Quellen
   matchen.

> Kleinere Abweichungen von ein bis zwei Zehntelprozentpunkten sind normal: Die
> Erhebung läuft weiter, und die Betriebspunkt-Ausschlüsse greifen über einen
> Namensfilter, der in Kibana etwas anders arbeitet als die Funktion
> `ist_betriebliche_haltestelle()` in den Notebooks.

---

## Priorität

Wenn die Zeit knapp wird, in dieser Reihenfolge:

1. **Grafik 1** — die vier Kernzahlen. Schnell gebaut, im Video am besten lesbar.
2. **Grafik 3** — die Karte. Stärkstes Bild und belegt die Geo-Fähigkeiten des Stacks.
3. **Grafik 2** — der Schwellenvergleich. Inhaltlich der Kern, aber aufwendiger.
4. Grafik 4 und 5 sind Reserve für die Fragerunde.
