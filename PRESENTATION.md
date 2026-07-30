# Storyboard — 6-Minuten-Video

**Gesamtlänge: 6:00.** Sprechtempo ~150 Wörter/Minute, also rund 900 Wörter.
Neun Szenen. Jede Zahl muss sich ihren Platz verdienen — was hier nicht steht,
kommt nicht vor.

**Roter Faden:** Die naheliegende Erklärung zuerst prüfen und verwerfen, dann den
Befund zeigen, der hält. Enden mit einer Maßnahme, die morgen umsetzbar ist.

---

## Szene 1 — Der Vorwurf (0:00–0:45)

Vier Beats. Die ersten beiden tragen das Gefühl, die letzten beiden benennen es.

### 1a — Die stehenden Trams (0:00–0:10)

**Bild:** Dein Video: mehrere Trams hintereinander, wartend.
**Ton:** Originalton oder Musik. **Kein Sprechtext.**

> **Regie:** Das Bild spricht für sich. Sobald du hier erklärst, nimmst du der
> Sequenz die Wirkung. Lieber zwei Sekunden zu lang stehen lassen als zu früh
> schneiden.

### 1b — Die fahrende U-Bahn (0:10–0:18)

**Bild:** Dein Video: U-Bahn fährt durch den Tunnel.
**Ton:** weiter ohne Sprechtext.

> **Regie:** Der Schnitt selbst ist die Aussage — Stillstand gegen Bewegung.
> Wenn möglich hart schneiden, nicht überblenden.

### 1c — Die Schlagzeilen (0:18–0:28)

**Bild:** Montage aus drei bis vier Zeitungsschlagzeilen, schnell geschnitten.

**Text (setzt hier ein):**
> Dieses Gefühl haben nicht nur wir.

### 1d — Die Frage (0:28–0:45)

**Bild:** Standbild — Tram und U-Bahn nebeneinander, oder Titelkarte.

**Text:**
> Die Straßenbahn gilt als das langsamere, unzuverlässigere Verkehrsmittel. Dabei
> gehören beide Netze der BVG, beide fahren auf Schienen, beide durch dieselbe Stadt.
>
> Ich habe drei Monate lang gemessen. 11,6 Millionen Tram-Abfahrten,
> 6,3 Millionen bei der U-Bahn — gleichzeitig, mit demselben Verfahren.
>
> **Stimmt das Gefühl?**

---

## Szene 2 — Die naheliegende Erklärung (0:45–1:15)

**Bild:** Karte aus `03_lsa_analyse.ipynb`, Abschnitt 5 (`lsa_karte.html`) —
Haltestellen nach LSA-Status eingefärbt.

**Text:**
> Nehmen wir zunächst an, es stimmt. Woran läge es dann?
>
> Der übliche Verdächtige ist die Ampelschaltung. Berlin hat elf Kreuzungen, an
> denen die Straßenbahn dokumentiert keinen Vorrang bekommt. Und tatsächlich:
> An vier davon entsteht rund zwanzigmal so viel Verspätung wie im Netzdurchschnitt.
> Das sieht nach einer klaren Antwort aus.

> **Regie:** Der erste Satz ist wichtig. Er hält die Frage aus Szene 1 offen,
> ohne dass sie in der Luft hängt — der Zuschauer weiß, dass die Antwort kommt,
> und akzeptiert den Umweg.

---

## Szene 3 — …die nicht hält (1:15–1:55)

**Bild:** Box-Plot aus `03_lsa_analyse.ipynb`, Abschnitt 4d — die vier LSA-Gruppen.
Daneben die Tabelle mit den Begründungen aus Abschnitt 4e.

**Text:**
> Nur steht in der Drucksache auch, *warum* der Vorrang fehlt. Bei drei der vier
> Anlagen lautet der Grund: Gleisschäden. Die Ampel ist abgeschaltet, **weil** das
> Gleis kaputt ist. Was die Verspätung verursacht — die fehlende Ampel oder der
> Gleisschaden — lässt sich nicht trennen.
>
> Und die sieben Anlagen am Alexanderplatz, wo aus Sicherheitsgründen bewusst kein
> Vorrang eingerichtet wurde? Dort entsteht überhaupt keine Mehrverspätung.
>
> Die naheliegende Erklärung trägt also nicht. Also habe ich anders gefragt.

> **Regie-Hinweis:** Diese Szene ist das methodische Herzstück. Nicht kürzen.
> Sie zeigt, dass geprüft und verworfen wurde — nicht nur bestätigt.

---

## Szene 4 — Der Mittelwert lügt (1:55–2:45)

**Bild zuerst:** dein Kibana-Screenshot mit den Verspätungsverteilungen beider Netze.
**Bild danach:** Effektstärken-Balken aus `02_eda.ipynb`, Abschnitt 6.

**Text:**
> Im Mittel liegt die Tram bei 33 Sekunden Verspätung, die U-Bahn bei 22. Zehn
> Sekunden Unterschied — damit lässt sich keine Schlagzeile begründen.
>
> Aber der Mittelwert verdeckt das Wesentliche. Ich habe drei Kennzahlen auf
> Haltestellenebene getestet:
>
> Beim **Durchschnitt** ist der Unterschied klein.
> Bei der **Zuverlässigkeit** ist er groß.
> Bei den **Verfrühungen** ist er der stärkste Effekt der gesamten Arbeit.
>
> Fast jede dritte Tram-Abfahrt liegt außerhalb des Pünktlichkeitsfensters. Bei der
> U-Bahn ist es jede zehnte.

---

## Szene 5 — Zu früh ist schlimmer als zu spät (2:45–3:20)

**Bild:** gestapelter Balken aus `01_eda.ipynb`, Abschnitt 3b
(zu früh / pünktlich / zu spät, beide Netze).

**Text:**
> Und die häufigere Abweichung ist die, über die niemand spricht: Jede fünfte Tram
> fährt zu **früh**. Bei der U-Bahn ist es jede zwanzigste.
>
> Für Fahrgäste ist das schlimmer als eine Verspätung. Wer pünktlich zur Fahrplanzeit
> an der Haltestelle steht und die Bahn ist weg, wartet nicht eine Minute — sondern
> bis zur nächsten. Auf der Linie 27 sind das im Schnitt dreieinhalb Minuten
> Verlust pro Fahrt.
>
> Die Tram ist also nicht langsamer als die U-Bahn. Sie ist **unberechenbarer**.

---

## Szene 6 — Und zwar nur an bestimmten Orten (3:20–3:50)

**Bild:** Konzentrationskurve aus `04_delay_propagation.ipynb`, Abschnitt 7.

**Text:**
> Das Problem ist nicht das System, sondern der Ort. Ein Fünftel der Streckenabschnitte
> erzeugt mehr als die Hälfte der gesamten Verspätung. Und umgekehrt: Ein Fünftel
> aller Tram-Haltestellen ist **zuverlässiger als die durchschnittliche
> U-Bahn-Station**.
>
> Wenn dieselbe Technik an manchen Orten funktioniert und an anderen nicht, dann
> liegt es nicht an der Technik.

---

## Szene 7 — Was zu tun wäre (3:50–4:50)

**Bild:** Maßnahmen-Ranking aus `06_entscheidungshilfe.ipynb`, Abschnitt 1.

**Text:**
> Drei Maßnahmen lassen sich aus den Daten ableiten. Zusammen kosten sie gut drei
> Millionen Euro. Das entspricht **sechs Metern U-Bahn-Tunnel**.
>
> Aber die wirksamste von ihnen kostet gar nichts: **Abfahrtsdisziplin**. Keine
> Baumaßnahme, nur Haltezeitvorgaben und Rückmeldung an die Fahrdienste. Sie betrifft
> ein Fünftel aller Abfahrten und spart geschätzt fünf Millionen Personenstunden im
> Jahr.
>
> Zum Vergleich: Die Gleissanierung bringt rund neunzigtausend Personenstunden — für
> hunderttausend Euro jährlich.
>
> Der gesellschaftliche Schaden durch Verspätung liegt bei rund 48 Millionen Euro im
> Jahr. Der direkte Budgetschaden der BVG bei 1,6 Millionen. Ein Verhältnis von
> **eins zu dreißig** — deshalb rechnet sich aus Sicht des Verkehrsbetriebs nie, was
> gesellschaftlich hoch rentabel wäre.

---

## Szene 8 — Die Gegenrechnung (4:50–5:25)

**Bild:** Störungsvergleich aus `05_kosten.ipynb`, Abschnitt 5.

**Text:**
> Ein Vorbehalt, der wichtig ist: Ich habe von April bis Juli gemessen — im
> **Bestfall der Straßenbahn**. Vereiste Oberleitungen, Laub, Schneeräumung fallen
> alle außerhalb meines Messzeitraums.
>
> Und der Mechanismus ist trotzdem sichtbar: **19 wetterbedingte Störungsmeldungen
> bei der Tram — bei der U-Bahn null.** Betriebsunterbrechungen treten bei der
> Straßenbahn fünfmal häufiger auf.
>
> Der gemessene Abstand ist also eine Untergrenze. Im Winter dürfte er größer sein.

---

## Szene 9 — Schluss (5:25–6:00)

**Bild:** Kostenvergleich Tram/U-Bahn je Kilometer aus `05_kosten.ipynb`,
Abschnitt 3. Am Ende Standbild mit den drei Kernsätzen.

**Text:**
> Ein Kilometer U-Bahn kostet so viel wie 13 bis 25 Kilometer Straßenbahn. Auch
> kapazitätsbereinigt bleibt die Tram um den Faktor vier bis acht günstiger. Für
> Berlin ist der Tram-Ausbau die einzige bezahlbare Option —
>
> **aber nur, wenn Winterfestigkeit mitfinanziert wird.** Sonst kauft die Stadt
> Netzreichweite und verliert genau die Zuverlässigkeit, bei der die Tram ohnehin
> schon dreifach zurückliegt.
>
> Und das Wirksamste, was Berlin morgen tun könnte, steht in keinem Investitionsplan.
> Es kostet nichts.

---

## Zeitbudget im Überblick

| Szene | Inhalt | Dauer | kumuliert |
|---|---|---|---|
| 1a | Stehende Trams (ohne Text) | 0:10 | 0:10 |
| 1b | Fahrende U-Bahn (ohne Text) | 0:08 | 0:18 |
| 1c | Schlagzeilen | 0:10 | 0:28 |
| 1d | Das Gefühl benennen + die Frage | 0:17 | 0:45 |
| 2 | Naheliegende Erklärung: Ampeln | 0:30 | 1:15 |
| 3 | …die nicht hält | 0:40 | 1:55 |
| 4 | Der Mittelwert lügt | 0:50 | 2:45 |
| 5 | Zu früh ist schlimmer | 0:35 | 3:20 |
| 6 | Konzentration auf wenige Orte | 0:30 | 3:50 |
| 7 | Handlungsempfehlung | 1:00 | 4:50 |
| 8 | Gegenrechnung Resilienz | 0:35 | 5:25 |
| 9 | Schluss | 0:35 | 6:00 |

**Die ersten 18 Sekunden laufen ohne Sprechtext.** Das ist ungewöhnlich viel für
sechs Minuten, aber es ist die einzige Stelle, an der du nicht argumentierst, sondern
zeigst. Die Zeit ist an drei Stellen wieder eingespart (Szene 2, 5 und 8).

---

## Grafiken — Herkunft

| Szene | Grafik | Quelle |
|---|---|---|
| 2 | LSA-Karte | `03_lsa_analyse.ipynb` § 5 → `lsa_karte.html` |
| 3 | Box-Plot LSA-Gruppen + Begründungstabelle | `03_lsa_analyse.ipynb` § 4d, § 4e |
| 4 | Verspätungsverteilung beider Netze | **Kibana-Screenshot** |
| 4 | Effektstärken-Balken | `02_eda.ipynb` § 6 |
| 5 | Pünktlichkeitsfenster gestapelt | `01_eda.ipynb` § 3b |
| 6 | Konzentrationskurve (Lorenz) | `04_delay_propagation.ipynb` § 7 |
| 7 | Maßnahmen-Ranking | `06_entscheidungshilfe.ipynb` § 1 |
| 8 | Störungsvergleich | `05_kosten.ipynb` § 5 |
| 9 | Baukosten je km | `05_kosten.ipynb` § 3 |

---

## Was bewusst **nicht** vorkommt

Für sechs Minuten zu viel Material. Bleibt im Notebook, kann in der Fragerunde
nachgereicht werden:

- Hypothesen H1–H4 und die n-Inflation (methodisch stark, erzählerisch zu langsam)
- Die Minutenquantisierung von `delay_s`
- Der Collector-Ausfall und der `cancelled`-Bruch
- Das Vorhersagemodell aus Notebook 06 — als **Backup-Folie** bereithalten, falls
  nach praktischem Nutzen gefragt wird
- Der historische Westberlin-Kontext (Szene 9 deutet ihn nur an)
- Der Gegenbefund, dass die U-Bahn häufiger ausfällt als die Tram

---

## Sprachliche Hinweise

- **Zahlen runden.** „Rund zwanzigmal", nicht „19,7-mal". Im Video kann niemand
  mitschreiben.
- **Höchstens eine Zahl pro Satz.** Zwei Zahlen in einem Satz gehen im Vortrag
  verloren.
- **Szene 3 nicht entschuldigen.** Ein verworfener Befund ist kein Scheitern,
  sondern der Beleg dafür, dass sauber geprüft wurde. Der Ton bleibt sachlich, nicht
  bedauernd.
- **Der letzte Satz ist die Pointe.** Danach nichts mehr sagen.
