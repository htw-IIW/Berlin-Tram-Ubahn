# Kibana-Visualisierungen

Anleitung für die Visualisierungen, die im Video verwendet werden und zugleich den
NoSQL-Teil der Abgabe belegen.

**Vorbereitung:** `python -m src.elasticsearch.kibana_setup` legt die Data Views an.
Kibana läuft auf http://localhost:5601, Login `elastic` / `changeme`.

---

## Vor allem anderen: die Filter

**Kibana zeigt sonst andere Zahlen als die Notebooks.** Damit Video und Analyse
zusammenpassen, müssen dieselben Ausschlüsse gelten (Herleitung in
`notebooks/01_eda.ipynb`, Abschnitt 2b).

Diese Filter gehören in **jede** Visualisierung:

```
delay_s: *
and not stop_name: ("Betriebshof*" or "*[Ausstieg]" or "*[Endstelle]")
```

**Zeitraum** oben rechts: `2026-04-27` bis `2026-07-29`.

**Zusätzlich bei allem, was Raten oder Zeitverläufe zeigt** — den Collector-Ausfall
ausklammern:

```
not (collected_at >= "2026-06-27" and collected_at < "2026-07-08")
```

> Für reine Verteilungsdarstellungen (Visualisierung 1) ist der Ausfall unkritisch:
> Es fehlen Beobachtungen, die Form der Verteilung ändert sich dadurch nicht.
>
> **Für Ausfallquoten gilt zusätzlich** `collected_at < "2026-06-27"` — danach ist die
> `cancelled`-Erfassung der U-Bahn nachweislich defekt (DATASET.md, Punkt 3).

---

## 1 — Verspätungsverteilung beider Netze *(Pflicht, Szene 4)*

Die zentrale Grafik des Videos. Sie zeigt, warum der Mittelwertvergleich in die Irre
führt: Die Verteilungen liegen fast übereinander, aber die Tram hat den viel längeren
Schwanz.

| | |
|---|---|
| **Typ** | Lens → *Bar vertical stacked* oder *Area* |
| **Data View** | `tram-departures*` und `ubahn-departures*` |
| **Horizontale Achse** | `delay_s`, Intervalle von **60** |
| **Vertikale Achse** | *Count of records*, **normiert auf Prozent** |
| **Aufteilung** | eine Ebene je Netz |

**So bekommst du beide Netze in ein Diagramm:** Lens kann nur eine Data View je Ebene.
Lege deshalb eine gemeinsame Data View über beide Indizes an —
*Stack Management → Data Views → Create*, Index-Pattern `*-departures-v2`. Dann kannst
du nach dem Feld `_index` aufteilen.

**Einstellungen, die den Unterschied machen:**
- Achsenbereich auf **−300 bis +600 Sekunden** begrenzen. Sonst quetscht der Ausreißer
  bei 3540 s alles zusammen.
- **„Normalize by unit" bzw. Prozent** statt absoluter Zahlen — sonst sieht man nur,
  dass die Tram mehr Abfahrten hat.
- Farben: Tram rot (`#E53935`), U-Bahn blau (`#1E88E5`) — durchgängig im ganzen Video.

**Was in der Bildunterschrift stehen sollte:** *n = 9,8 Mio. (Tram) bzw. 5,5 Mio.
(U-Bahn) Abfahrten, April–Juli 2026.*

---

## 2 — Verspätungskarte *(Empfehlung, Szene 6)*

Zeigt die geografische Konzentration und nutzt das `geo_point`-Mapping — ein
Kibana-Merkmal, das eine reine Python-Auswertung nicht bietet. Gutes Argument für den
NoSQL-Teil.

| | |
|---|---|
| **Typ** | **Maps** |
| **Data View** | `tram-departures-v2` |
| **Layer** | *Clusters and grids* auf `stop_location` |
| **Metrik** | `Average of delay_s` |
| **Farbskala** | *Yellow to Red*, Bereich 0–90 s |
| **Größe** | nach *Count of records* |

Zoom auf das Tram-Netz im Osten. Kachelgröße so wählen, dass einzelne Haltestellen
erkennbar bleiben — bei zu grober Auflösung verschwinden die Hotspots im Mittelwert.

> **Alternative mit mehr Aussagekraft:** Statt der mittleren Verspätung den
> **Anteil über 180 s** darstellen. Dafür einen Filter `delay_s >= 180` setzen und als
> Metrik *Count* wählen, dann durch die Gesamtzahl teilen — oder einfacher: die
> Karte aus `notebooks/03_lsa_analyse.ipynb` (`lsa_karte.html`) nehmen, die das
> bereits kann.

---

## 3 — Tagesgang Tram gegen U-Bahn *(optional, Reserve)*

| | |
|---|---|
| **Typ** | Lens → *Line* |
| **Horizontale Achse** | `hour_of_day`, Intervall 1 |
| **Vertikale Achse** | `Average of delay_s` |
| **Aufteilung** | nach `_index` |

Zeigt, dass die Tram über den ganzen Tag über der U-Bahn liegt — und dass beide nachts
nicht besser werden. Ergänzt Szene 4, falls dort Zeit übrig ist.

---

## 4 — Ausfallquote im Zeitverlauf *(nur als Beleg, nicht fürs Video)*

Dokumentiert den Erfassungsbruch, den die Analyse aufgedeckt hat.

| | |
|---|---|
| **Typ** | Lens → *Line* |
| **Horizontale Achse** | `collected_at`, täglich |
| **Vertikale Achse** | *Count of records* mit Filter `cancelled: true`, geteilt durch Gesamtzahl |
| **Aufteilung** | nach `_index` |
| **Zeitraum** | ganzer Erhebungszeitraum, **ohne** Ausfallfilter |

Man sieht den Einbruch der U-Bahn-Kurve am 8. Juli, während die Tram-Kurve unverändert
weiterläuft. Für die **Fragerunde** als Beleg für die Datenqualitätsprüfung — im Video
ist dafür keine Zeit.

---

## 5 — Störungsmeldungen nach Art *(optional, Szene 8)*

| | |
|---|---|
| **Typ** | Lens → *Bar horizontal* |
| **Data View** | `*-disruptions` |
| **Vertikale Achse** | `summary.keyword`, Top 10 |
| **Horizontale Achse** | **Unique count of `valid_from`** |
| **Aufteilung** | nach `_index` |
| **Filter** | `not text: "Test - Please ignore*"` |

> **Wichtig:** Als Metrik **nicht** *Count of records* verwenden. Eine Störung erzeugt
> ein Dokument je betroffener Fahrt und Haltestelle — eine dreiwöchige Baustelle allein
> erzeugt Hunderttausende. *Unique count of `valid_from`* nähert die Zahl der
> tatsächlichen Vorfälle an. Begründung in DATASET.md, Punkt 7.

Erwartetes Bild: Bei der U-Bahn dominieren defekte Aufzüge (86 % der Vorfälle), bei der
Tram Betriebsunterbrechungen und Umleitungen.

---

## Screenshots aufnehmen

- **Dunkles Kibana-Theme** verwenden. Es passt zu den rbb24-Grafiken, und weiße
  Flächen blenden im Video.
- Browserfenster auf **1920 × 1080** ziehen, dann mit `Cmd+Shift+4`, Leertaste, Klick
  nur das Panel aufnehmen — nicht den ganzen Bildschirm mit Menüleiste.
- **Legende und Achsenbeschriftungen vergrößern**: In Lens unter *Appearance* die
  Schriftgröße hochsetzen. Was am Monitor lesbar ist, ist im Video oft zu klein.
- Panel-Titel so formulieren, dass er ohne Erklärung verständlich ist — im Video liest
  ihn niemand zweimal.

---

## Priorität

Wenn die Zeit knapp wird:

1. **Visualisierung 1** — die braucht das Video, dafür gibt es keinen Ersatz.
2. **Visualisierung 2** — starkes Bild und belegt die Geo-Fähigkeiten des Stacks.
3. Der Rest ist Reserve für die Fragerunde.
