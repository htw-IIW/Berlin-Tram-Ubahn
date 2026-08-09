# Storyboard — 6-Minuten-Video

**Gesamtlänge: 6:00.** Sprechtempo ~150 Wörter/Minute, also rund 900 Wörter.
Neun Szenen. Jede Zahl muss sich ihren Platz verdienen — was hier nicht steht,
kommt nicht vor.

**Roter Faden:** Erst messen, wie groß der Unterschied zwischen Tram und U-Bahn
wirklich ist. Dann zeigen, dass er nicht am System hängt, sondern an wenigen Orten.
Dann an diesen Orten die naheliegende Erklärung prüfen — und verwerfen. Enden mit
einer Maßnahme, die morgen umsetzbar ist, und einem Ausblick, der nichts kostet.

> **Umgestellt am 09.08.2026.** Bis dahin standen die beiden LSA-Szenen an Position
> 2 und 3. Zwei Gründe für den Tausch: Die LSA-Analyse misst **erzeugte** Verspätung,
> ein Begriff, der erst in der Ortsszene eingeführt wird — vorher musste er umschrieben
> werden. Und eine Ursache lässt sich nicht beurteilen, bevor klar ist, wie groß das
> Problem überhaupt ist. Die LSA-Szenen sind damit kein Rateversuch mehr, sondern das
> Nachbohren an den Hotspots, die eine Szene vorher auf der Karte zu sehen waren.

---

---

## Szene 1 — Der Vorwurf (0:00–0:45)

Vier Beats. Die ersten beiden tragen das Gefühl, die letzten beiden benennen es.

### 1a — Die stehenden Trams (0:00–0:10)

**Bild:** Dein Video: mehrere Trams hintereinander, wartend.
**Ton:** Originalton oder Musik. **Kein Sprechtext.**


### 1b — Die fahrende U-Bahn (0:10–0:18)

**Bild:** Dein Video: U-Bahn fährt durch den Tunnel.
**Ton:** weiter ohne Sprechtext.


### 1c — Die Schlagzeilen und die Belege (0:18–0:33)

**Bild**: links Ubahn rechts Tram
> zwei Berliner verkehrsmittel, beide auf Schiene, beide betrieben durch die BVG. Dennoch fühlt sich die Tram oft langsam, zu spät und unzuverlässig an.

**Bild, Teil 1:** Montage aus drei bis vier Zeitungsschlagzeilen, schnell geschnitten.
> Nicht selten sorgt sie damit auch für diverse negative Schlagzeilen.

**Bild** Fahrplan Tram
> Und dennoch ist nicht ersetzbar: Die Tram erschließt Ortsteile, in die keine U-Bahn
> fährt. Wer dort wohnt, ha

> **Warum umformuliert:** Der frühere Satz („eines der ältesten und größten
> Straßenbahnnetze der Welt…") war reine Beschreibung — richtig, aber ohne Folge.
> Die neue Fassung nennt dieselbe Tatsache als **Einsatz**: Sie begründet, warum
> die Frage überhaupt zählt, und nimmt gleichzeitig den naheliegenden Einwand
> „dann baut eben U-Bahn" vorweg. Szene 9 zahlt darauf ein.
**Bild, Teil 2:** rbb24-Grafik *„Durchschnittsgeschwindigkeit der Berliner
Straßenbahn"* (19,1 km/h in 2017 → 17,3 km/h in 2024, Quelle BVG).
> Die durchschnittliche Geschwindigkeit der Tram
> in sieben Jahren von 19 auf 17 Kilometer pro Stunde langsamer geworden. (Damit ist sie kaum schneller als ein Bus im Autoverkehr)

> Aber ist die Tram wirklich unzuverlässiger als die Ubahn und wenn ja warum?


### 1d — Die Frage (0:33–0:47)

**Bild:** Standbild — Tram und U-Bahn nebeneinander, oder Titelkarte.

**Text:**

> Um dieses Verhalten und mögliche Ursachen selbst zu untersuchen
> habe ich drei Monate lang alle Abfahrtsdaten der Berliner Tram und U-Bahn gesammelt. 11,6 Millionen Tram-Abfahrten,
> 6,3 Millionen bei der U-Bahn — gleichzeitig, mit demselben Verfahren.

> 
> **Woran liegt es?**

---

## Szene 2 — Der Mittelwert lügt (0:47–1:16)

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

## Szene 3 — Zu früh ist schlimmer als zu spät (1:16–1:56)

**Bild, Teil 1:** rbb24-Grafik *„Verspätungen und Verfrühungen bei der BVG 2025"*
(Quelle: Senatsverwaltung für Verkehr).
**Bild, Teil 2:** gestapelter Balken aus `01_eda.ipynb`, Abschnitt 3b.

**Text:**
> Und die häufigere Abweichung ist die, über die niemand spricht: Die Tram fährt
> häufig zu **früh**.
>
> Die amtliche Statistik weist das aus — und zwar drastisch: Die Straßenbahn fährt
> **fünfzehnmal so oft zu früh wie die U-Bahn**. Meine eigene Messung kommt auf einen
> geringeren, aber gleichgerichteten Abstand.
>
> Für Fahrgäste ist eine Verfrühung schlimmer als eine Verspätung. Wer pünktlich zur
> Fahrplanzeit an der Haltestelle steht und die Bahn ist weg, wartet nicht eine
> Minute — sondern bis zur nächsten. Auf der Linie 27 sind das im Schnitt dreieinhalb
> Minuten pro Fahrt.
>
> Die Tram ist also nicht einfach langsamer. Sie ist **unberechenbarer**.

> **Regie und Absicherung:** Die amtlichen Anteile (Tram 3,53 % zu früh) und meine
> (19,2 %) unterscheiden sich um Faktor fünf, weil der Senat je Fahrt zählt und ich je
> Halt. **Nenne im Video keine der beiden absoluten Zahlen direkt neben der anderen.**
> Sprich bei der amtlichen Grafik vom **Verhältnis** („fünfzehnmal so oft"), bei deiner
> vom **Mechanismus** („jede fünfte Abfahrt an einem Halt"). So entsteht kein
> scheinbarer Widerspruch.
>
> Falls in der Fragerunde nachgehakt wird — die Erklärung steht unten unter
> „Verhältnis zur amtlichen Statistik".

---

## Szene 4 — Und zwar nur an bestimmten Orten (1:56–2:39)

**Bild, Teil 1:** Konzentrationskurve aus `04_delay_propagation.ipynb`, Abschnitt 7.
**Bild, Teil 2:** `lsa_karte.html` aus `03_lsa_analyse.ipynb`, Abschnitt 5 — Kreisgröße
= **mittlere** Verspätung. Hier zum ersten Mal im Bild.
**Bild, Teil 3:** `karte_erzeugte_verspaetung.html` — **derselbe Ausschnitt, andere
Größe.** Blau baut Verspätung ab, rot erzeugt sie.

**Text:**
> Das Problem ist nicht das System, sondern der Ort. Ein Fünftel der Streckenabschnitte
> erzeugt mehr als die Hälfte der gesamten Verspätung. Und umgekehrt: Ein Fünftel
> aller Tram-Haltestellen ist **zuverlässiger als die durchschnittliche
> U-Bahn-Station**.
>
> Dieselbe Karte wie eben, nur färbe ich jetzt nicht mehr danach, wie spät eine Bahn
> dort ist, sondern danach, wie viel Verspätung dort **dazukommt**. Das Bild kippt.
> Rosa-Luxemburg-Platz zum Beispiel: eben noch tiefrot, jetzt blau. Die Haltestelle
> ist nicht das Problem, sie **erbt** es von weiter oben auf der Linie — und baut
> unterwegs sogar wieder Verspätung ab.
>
> Wenn dieselbe Technik an manchen Orten funktioniert und an anderen nicht, dann
> liegt es nicht an der Technik.

> **Regie:** Der Schnitt zwischen den beiden Karten ist der stärkste Bildmoment der
> Arbeit — gleicher Ausschnitt, gleiche Zoomstufe, nur die Färbung wechselt. Beide
> Karten vorher im Browser auf **denselben Kartenausschnitt** ziehen und die Legende
> an dieselbe Stelle schieben, sonst geht der Effekt verloren.
>
> **Neu seit der Umstellung:** Die Karte mit der *mittleren* Verspätung lief früher in
> Szene 2 und wurde hier nur wiederverwendet. Jetzt läuft sie hier zuerst. Das ist die
> bessere Lösung — das Kartenpaar gehört in eine Szene, nicht über vier Minuten
> verteilt. In Szene 5 kommt dieselbe Karte ein drittes Mal, dann nach LSA-Status
> eingefärbt; der Zuschauer kennt den Ausschnitt dann bereits und muss sich nur noch
> auf die Farbe konzentrieren.
>
> Die beiden Größen hängen fast nicht zusammen: **ρ = 0,25**. Wo man ankommt und wo
> das Problem entsteht, sind zwei verschiedene Karten. Genau deshalb reicht die erste
> nicht aus, um zu handeln.

---

## Szene 5 — Die naheliegende Erklärung (2:39–3:34)

**Bild** Ampel
> Die erste Vermutung fiel auf die Ampel. Anders als die U-Bahn ist die Tram Teil des Straßenverkehrs — und kann von ihm ausgebremst werden. 

**Bild:** kurzer Einschub (2–3 s) — Screenshot der GovData-Seite
`https://www.govdata.de/suche/daten/lichtsignalanlagene6003`, Datensatz

> Zur Untersuchung habe ich meine Daten um den Standort und Status aller Berliner Lichtsignalanlagen, kurz LSA ergänzt.

**Bild: Signal Tram**
> Der Berliner Senat nennt die für den ÖPNV relevanten LSAs mit Signalverarbeitung Ampeln mit ÖPNV **Beeinflussung** 
> Dabei handelt es sich um Ampeln, an denen die Tram ein Signal sendet und damit möglichst bevorzugt geschaltet wird.


**Bild: Ampeln**
> Haben Haltestellen an Ampeln ohne ÖPNV-Beeinflussung also mehr Verspätung?

*„Lage und die Bezeichnung der Lichtsignalanlagen"*, danach Schnitt auf die
Karte aus `03_lsa_analyse.ipynb`, Abschnitt 5 (`lsa_karte.html`) —
Haltestellen nach LSA-Status eingefärbt, Kreisgröße = mittlere Verspätung.
> Auf der Karte sehen wir alle Berliner Tram-Haltestellen. Je größer der Radius, desto größer die durchschnittliche Verspätung der Trams an dieser Haltestelle
>Die grünen Kreise zeigen alle Haltstellen mit aktiver LSA-Beeinflussung in einem Umkreis von 50m um die Haltestelle, die grauen zeigen alle ohne LSA-Beeinflussung

> Zusätzlich nennt eine parlamentarische Anfrage von 2024 sechs Kreuzungen, an denen diese
> Beeinflussung abgeschaltet ist. Diese sind rot gekennzeichnet.

---

## Szene 6 — …die nicht hält (3:34–4:21)

**Bild:** Balkendiagramm `szene3b_lsa_balken.png` aus `03_lsa_analyse.ipynb`,


> Die Grafik zeigt die durchschnittlich erzeugte Verspätung an den Haltestellen nach LSA Gruppen: nicht vorhanden, aktiv, aktiv aber mit auffälliger Verspätung und die bestätigten inaktiven.
> Und tatsächlich: an den Haltestellen mit bestätigt inaktiver LSA kommt rund vierzehnmal so viel Verspätung dazu wie im restlichen
> Netz.

> Die Parlamentarische Anfrage nennt auch, warum die Beeinflussung an den jeweiligen Haltestellen fehlt. 

**Bild:** Screenshot aus der parlamentarischen Anfrage
> Bei zwei der
> sechs Anlagen lautet der Grund: Gleisschäden. Die Ampel ist abgeschaltet,
> **weil** das Gleis kaputt ist. Was die Verspätung verursacht — die fehlende
> Beeinflussung oder der Gleisschaden — lässt sich nicht trennen. Der Senat
> schreibt es selbst: Bei Langsamfahrstellen wegen Gleisschäden lohnt die
> Umprogrammierung nicht, also wird auf ein Festzeitprogramm umgestellt.
>
> Bei den übrigen vier: ein Knotenumbau, veraltete Technik, eine fremde Baustelle.
> Und eine davon baut sogar Verspätung **ab**.
>
> Sechs Anlagen, sechs verschiedene Gründe — und keiner davon ist die Ampel selbst.
> Die naheliegende Erklärung trägt also nicht — und das ist die eigentliche
> Auskunft: An diesen Orten muss das Geld nicht in die Ampel, sondern ins Gleis.

> Die Gruppe der Haltestellen ohne AMpelbeeinflussung hat dabei die geringste durchschnittliche erzeugte Verspätung. 






> **Erledigt durch die Umstellung.** Dieser Block erklärte früher, warum die
> „vierzehnmal" nicht in Szene 2 stehen durfte: Dort lag die Karte mit der
> **mittleren** Verspätung im Bild, während die Zahl die **erzeugte** meint — und
> der Begriff war noch nicht eingeführt. Beides ist jetzt gelöst, weil Szene 4
> die erzeugte Verspätung definiert und zeigt, bevor diese Szene kommt.
>
> **Was bleibt:** Den ersten Satz erst sprechen, wenn die Balken stehen. Und die
> Zahl selbst ist heikel — siehe den Absicherungsblock direkt darunter.

> **Absicherung.** Der Effekt ist nach der Korrektur schwächer, aber weiterhin
> signifikant: rund **+5 bis +6 s** gegen **rund +0,5 s** im Netz, Mann-Whitney-U
> einseitig **p ≈ 0,02**, rang-biseriale Effektstärke **r ≈ +0,50**. Das ist nach
> der Einordnung dieses Projekts ein **großer** Effekt, nicht ein mittlerer — die
> Schwelle für „groß" liegt bei 0,5. Kein Widerspruch zum knappen p-Wert: Bei
> n = 6 ist Signifikanz nur mit einem großen Effekt erreichbar.
>
> **Den Faktor „vierzehnmal" besser nicht sagen.** Er ist der Quotient zweier
> winziger Mediane; je nach geladener Datenmenge liegt er zwischen rund neun und
> rund vierzehn, ohne dass sich am Befund etwas ändert. Belastbar ist die
> **Differenz** — rund fünf Sekunden mehr erzeugte Verspätung je Halt, abgesichert
> durch das Hodges-Lehmann-Intervall in `03_lsa_analyse.ipynb`, Abschnitt 4d-2.
>
> **Neu und stark: das Tagesprofil.** Der Unterschied ist nachts genauso groß wie
> zur Hauptverkehrszeit (r ≈ 0,47 in allen drei Tageszeiten). Eine
> Beeinflussungsanlage kann nachts kaum wirken — steht kein Verkehr im Weg, gibt es
> nichts zu bevorrechtigen. Ein Gleisschaden wirkt rund um die Uhr. Das ist der
> stärkste verfügbare Hinweis, und er zeigt **weg** von der Ampel.


> Falls in der Fragerunde nachgehakt wird, welche Anlage Verspätung abbaut:
> Berliner Allee / Buschallee, −8,4 s. Grund laut Drucksache eine Maßnahme der
> Berliner Wasserbetriebe, also gar keine Verkehrsursache. Genau dieser Fall
> zeigt, warum die Gruppe keine kausale Aussage trägt.

---

## Szene 7 — Was zu tun wäre (4:21–5:15)

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

**Bild, Ausblick:** Standbild mit den beiden Begriffen nebeneinander —
*Beeinflussung* gegen *Vorrang*.

**Text, Ausblick:**
> Und eine vierte Maßnahme steht in keinem Ranking, weil sie nichts kostet. Berlin
> gibt der Tram an den Kreuzungen keinen **Vorrang**. Es gibt ihr **Beeinflussung**:
> Die Bahn darf sich anmelden, mehr nicht. Das steht so in der Antwort des Senats.
> Das ist keine technische Grenze, sondern eine Entscheidung darüber, wem die
> Grünzeit gehört.
>
> Eine Modellrechnung aus diesem Jahr zeigt, was daran hängt: Gibt man dem Auto mehr
> Grün, wird Autofahren **langsamer** — die günstigere Ampel holt zusätzliche Autos
> auf die Straße, und der Stau frisst den Gewinn auf. Schon kleine Verschiebungen
> zugunsten von Bus, Bahn und Rad kehren das um.
>
> Womöglich profitieren am Ende sogar die, denen man das Grün nimmt. Das ist die
> Vermutung, die dieses Modell nahelegt — geprüft habe ich sie nicht.

> **Regie und Absicherung — hier wird am ehesten nachgefragt.**
>
> **Erstens: kein Widerspruch zum Ranking.** In der Grafik steht „Signaltechnik
> erneuern" auf dem letzten Platz. Das ist etwas anderes als das hier. Sag den
> Unterschied ausdrücklich: **Nicht die Ampeln reparieren — die Ampeln anders
> programmieren.** Das erste ist Hardware und lohnt nach meinen Daten nicht, das
> zweite ist ein Signalprogramm und kostet nichts.
>
> **Zweitens: Diese Empfehlung folgt NICHT aus der LSA-Messung.** Szene 6 hat
> gezeigt, dass der Ampeleffekt nicht kausal interpretierbar ist. Der Satz hier
> stützt sich auf zwei andere Dinge: auf die **Drucksache**, die das Wort
> „Beeinflussung" selbst verwendet, und auf **fremde Literatur**. Formuliere es
> genau so — *„echten Vorrang gibt es in Berlin nicht, seine Wirkung kann in meinen
> Daten deshalb gar nicht auftauchen"*. Das ist die stärkste ehrliche Fassung: Du
> hast nicht gemessen, dass Vorrang nicht wirkt, sondern dass es ihn nicht gibt.
>
> **Drittens: die Quelle sauber nennen.** Cerioli, *Traffic light cycles for a
> sustainable city*, Royal Society Open Science, Mai 2026
> (`doi.org/10.1098/rsos.251118`). Es ist eine **Simulation**, keine Messung, und
> sie behandelt die Grünzeitverteilung zwischen Auto und allem anderen — nicht
> ÖPNV-Vorrangschaltungen im Speziellen. Ein Halbsatz „eine Modellrechnung aus
> diesem Jahr" reicht als Kennzeichnung im Video, die volle Angabe gehört auf die
> Backup-Folie.
>
> **Viertens: der Konjunktiv im letzten Satz ist Absicht.** Dass der Autoverkehr
> von einer Umverteilung profitiert, ist die naheliegende Umkehrung des
> Paradoxons — ausformuliert steht sie in der Quelle nicht. „Vermutung, geprüft
> habe ich sie nicht" kostet dich zwei Sekunden und nimmt der einzigen Frage die
> Spitze, die deinen Schluss sonst aufmachen könnte.

---

## Szene 8 — Die Gegenrechnung (5:15–5:40)

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

## Szene 9 — Schluss (5:40–6:13)

**Bild:** Kostenvergleich Tram/U-Bahn je Kilometer aus `05_kosten.ipynb`,
Abschnitt 3. Am Ende Standbild mit den drei Kernsätzen.

**Text:**
> Ein Kilometer U-Bahn kostet so viel wie 13 bis 25 Kilometer Straßenbahn — auch
> kapazitätsbereinigt bleibt die Tram um ein Mehrfaches günstiger.
>
> Und dass früher so viel U-Bahn gebaut wurde, trägt als Gegenargument nicht:
> Damals zahlte der Bund die Hälfte des West-Berliner Haushalts. Diese Lage
> besteht nicht mehr.
>
> Für Berlin ist der Tram-Ausbau damit die einzige bezahlbare Option —
>
> **aber nur, wenn Winterfestigkeit mitfinanziert wird.** Sonst kauft die Stadt
> Netzreichweite und verliert genau die Zuverlässigkeit, bei der die Tram ohnehin
> schon dreifach zurückliegt.

> **Regie und Absicherung:** Der Satz über den Bundeszuschuss ist bewusst eine
> **Finanzierungsaussage, keine Kostenaussage.** Notebook 05, Abschnitt 4 rechnet
> historische Baukosten ausdrücklich *nicht* in heutige Euro um — dafür gibt es
> keinen validierten Baukostenindex für den Berliner ÖPNV. Nenne deshalb keinen
> historischen Eurobetrag; das wäre die angreifbarste Zahl der ganzen
> Präsentation.
>
> Falls nachgefragt wird: 1962 flossen rund 1,1 Mrd. DM Bundeszuschuss jährlich
> bei einem Gesamthaushalt von gut 2 Mrd. DM. Quellen sind freigegebene
> US-State-Department-Dokumente, also Sekundärquellen — im Notebook als solche
> gekennzeichnet.
>
> Und das Wirksamste, was Berlin morgen tun könnte, steht in keinem Investitionsplan.
> Es kostet nichts.

---

## Zeitbudget im Überblick

Neu ausgezählt am 09.08.2026 nach der Umstellung, gegen 150 Wörter/Minute. Die
Spalte *nötig* ist der tatsächlich formulierte Text, nicht die Wunschdauer. Die
Reihenfolge ist neu, die Textmengen sind es nicht — bis auf den Ausblick in Szene 7.

| Szene | Inhalt | nötig | Budget | Differenz | war |
|---|---|---|---|---|---|
| 1a | Stehende Trams (ohne Text) | — | 0:10 | — | 1a |
| 1b | Fahrende U-Bahn (ohne Text) | — | 0:08 | — | 1b |
| 1c+1d | Schlagzeilen, Geschwindigkeit, die Frage | **0:51** | 0:40 | **+11 s** | 1c+1d |
| 2 | Der Mittelwert lügt | 0:29 | 0:32 | −2 s | 4 |
| 3 | Zu früh ist schlimmer | 0:40 | 0:40 | ±0 | 5 |
| 4 | Konzentration + Kartenwechsel | 0:43 | 0:44 | −1 s | 6 |
| 5 | Naheliegende Erklärung: Ampeln | **0:55** | 0:40 | **+15 s** | 2 |
| 6 | …die nicht hält | **0:47** | 0:42 | **+5 s** | 3 |
| 7 | Handlungsempfehlung | 0:42 | 0:44 | −2 s | 7 |
| 7 | **Ausblick Vorrang (neu)** | **0:12** | — | **+12 s** | — |
| 8 | Gegenrechnung Resilienz | 0:25 | 0:28 | −3 s | 8 |
| 9 | Schluss | 0:33 | 0:32 | +1 s | 9 |

**Der Text liegt bei rund 6:35 und muss um etwa 35–40 Sekunden kürzer werden.**
Das sind 10 Sekunden mehr als vor der Umstellung — der Ausblick kostet sie, und er
ist es wert. Die Umstellung selbst hat nichts hinzugefügt.

Die Überbuchung sitzt in drei Szenen, und nur dort:

- **Szene 5 (+15 s, vormals Szene 2).** Der Block über die Lichtsignalanlagen
  erklärt den Mechanismus zweimal: einmal als „Ampeln, an denen die Tram ein
  Signal sendet und damit möglichst bevorzugt geschaltet wird", einmal als
  „Der Berliner Senat nennt dieses System Ampel-Beeinflussung". Eine der beiden
  Erklärungen reicht. **Neuer Kürzungsgewinn durch die Umstellung:** Der Satz, der
  die Karte erklärt („Auf der Karte sehen wir alle Berliner Tram-Haltestellen, je
  größer der Radius…"), ist jetzt überflüssig — dieselbe Karte lief schon in
  Szene 4, der Zuschauer kennt sie. Das sind noch einmal rund 8 Sekunden.
- **1c+1d (+11 s).** Unverändert: Der Schlagzeilen-Satz und der Satz über die
  Unersetzbarkeit der Tram sagen beide, dass die Tram als unzuverlässig gilt und
  trotzdem gebraucht wird.
- **Szene 6 (+5 s, vormals Szene 3).** Nicht hier kürzen — das ist das methodische
  Herzstück.

Alle übrigen Szenen liegen im Budget oder knapp darunter.

**Rechnung, wenn du die drei naheliegenden Kürzungen machst:** doppelte
Mechanismus-Erklärung in Szene 5 (−7 s), überflüssige Kartenerklärung ebenda
(−8 s), Dopplung in 1c+1d (−11 s) — macht 6:09. Dann fehlen noch neun Sekunden,
und 1b von 0:08 auf 0:05 bringt drei davon.

**Die ersten 18 Sekunden laufen ohne Sprechtext.** Das ist ungewöhnlich viel für
sechs Minuten, aber es ist die einzige Stelle, an der du nicht argumentierst, sondern
zeigst. Wenn es am Ende nicht reicht, ist 1b (0:08 → 0:05) die schmerzloseste Kürzung.

---

## Grafiken — Herkunft

| Szene | Grafik | Quelle |
|---|---|---|
In Szenenreihenfolge. Die Spalte *war* nennt die alte Szenennummer, damit schon
exportierte Dateien und Notizen zuzuordnen bleiben.

| Szene | Grafik | Quelle | war |
|---|---|---|---|
| 1c | Durchschnittsgeschwindigkeit Tram 2017–2024 | **rbb24 / BVG** | 1c |
| 2 | Verspätungsverteilung beider Netze | **Kibana-Screenshot** | 4 |
| 2 | Effektstärken-Balken | `02_eda.ipynb` § 6 | 4 |
| 3 | Verspätungen und Verfrühungen BVG 2025 | **rbb24 / Senatsverwaltung** | 5 |
| 3 | Pünktlichkeitsfenster gestapelt | `01_eda.ipynb` § 3b | 5 |
| 4 | Konzentrationskurve (Lorenz) | `04_delay_propagation.ipynb` § 7 | 6 |
| 4 | LSA-Karte, **mittlere** Verspätung — **hier zuerst** | `03_lsa_analyse.ipynb` § 5 → `lsa_karte.html` | 2 |
| 4 | Karte der **erzeugten** Verspätung | `03_lsa_analyse.ipynb` § 5 → `karte_erzeugte_verspaetung.html` | 6 |
| 5 | Datensatz-Nachweis Lichtsignalanlagen | **GovData-Screenshot** — `govdata.de/suche/daten/lichtsignalanlagene6003` | 2 |
| 5 | Dieselbe Karte, nach LSA-Status eingefärbt | `03_lsa_analyse.ipynb` § 5 → `lsa_karte.html` | 2 |
| 6 | Balken der vier LSA-Gruppen | `03_lsa_analyse.ipynb` § 4d, § 4e → `szene3b_lsa_balken.png` | 3 |
| 6 | Begründungstabelle abgeschaltete Anlagen | **Drucksache-Screenshot** — Drs. 19/19804, Antwort 8/9, S. 3–4 | 3 |
| 7 | Maßnahmen-Ranking | `06_entscheidungshilfe.ipynb` § 1 | 7 |
| 7 | **Standbild „Beeinflussung gegen Vorrang" (neu)** | selbst gesetzte Titelkarte; Beleg Drs. 19/19804, Antwort 8/9 | — |
| 8 | Störungsvergleich | `05_kosten.ipynb` § 5 | 8 |
| 9 | Baukosten je km | `05_kosten.ipynb` § 3 | 9 |

> **Der Dateiname `szene3b_lsa_balken.png` stimmt nicht mehr.** Die Grafik gehört
> jetzt zu Szene 6. Nicht umbenennen — sie wird von `scripts/export_grafiken.py`
> unter diesem Namen erzeugt, und ein Umbenennen bräche den Export. Nur wissen.

---

## Verhältnis zur amtlichen Statistik

Die Senatsverwaltung weist für 2025 aus: Straßenbahn 3,53 % zu früh und 13,32 % zu spät,
U-Bahn 0,23 % und 1,70 %. Meine Messung kommt auf 19,2 % / 10,8 % bzw. 5,9 % / 4,0 %.

**Der Unterschied ist keine Widerlegung. Drei Effekte überlagern sich, und sie lassen
sich mit den veröffentlichten Angaben nicht trennen.**

**1. Andere Zähleinheit — vermutlich der stärkste Effekt.**
Der Senat zählt **je Fahrt**, diese Arbeit **je Abfahrtsereignis an einer Haltestelle**.
Eine Fahrt, die an drei von dreißig Halten zu früh ist, zählt amtlich nicht als
verfrüht — in meinen Daten dreimal.

**2. Nicht die Schwelle.**
Um die amtlichen Werte zu reproduzieren, bräuchte man für die Tram eine Schwelle von
etwa 150 Sekunden, für die U-Bahn von etwa 280. Zwei verschiedene Schwellen innerhalb
derselben Statistik gibt es nicht. Damit scheidet die Schwellenwahl als Erklärung aus.

**3. Anderer Zeitraum — wirkt nur bei der Verspätung, und dort wie erwartet.**
Die amtliche Zahl umfasst das ganze Jahr 2025, meine Messung April bis Juli 2026.

| | amtlich (Jahr) | eigene Messung (Sommer) | passt zur Saisonthese? |
|---|---|---|---|
| Tram, zu spät | 13,32 % | 10,8 % | **ja** — Jahr schlechter als Sommer |
| Tram, zu früh | 3,53 % | 19,2 % | nein — Winter macht Bahnen später, nicht früher |
| U-Bahn, zu spät | 1,70 % | 4,03 % | nein — Jahr müsste höher liegen, liegt niedriger |

Nur die erste Zeile lässt sich saisonal erklären — und sie stützt genau die These aus
Notebook 01, Befund 6: **Der Sommer ist der Bestfall der Straßenbahn**, das Jahresmittel
liegt höher. Die anderen beiden Zeilen zeigen, dass der Einheitenunterschied überwiegt.

> **Konsequenz für die Präsentation:** Die Niveaus der beiden Quellen sind **nicht
> vergleichbar** und dürfen nicht nebeneinandergestellt werden, als wären sie es. Nutze
> die amtliche Grafik ausschließlich für die **Richtung**.

**Entscheidend für die Argumentation:** Beide Quellen zeigen dieselbe Richtung, und die
amtliche Statistik zeigt den Abstand sogar **deutlich größer** als meine Messung:

| Verhältnis Tram : U-Bahn | amtlich | eigene Messung |
|---|---|---|
| Verfrühung | **15,3×** | 3,3× |
| Verspätung | **7,8×** | 2,7× |

> Die eigene Analyse ist gegenüber der amtlichen Statistik also **konservativ**. Wer
> ihr vorwirft, den Unterschied zu übertreiben, argumentiert gegen die Zahlen der
> Senatsverwaltung.

**Falls in der Fragerunde nach den Niveauunterschieden gefragt wird**, ist die kurze
Antwort: *„Der Senat zählt je Fahrt, ich je Halt — die Niveaus sind nicht vergleichbar.
Vergleichbar ist das Verhältnis zwischen den Netzen, und da fällt die Tram amtlich sogar
deutlicher ab als bei mir."*

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
- **Szene 6 nicht entschuldigen.** Ein verworfener Befund ist kein Scheitern,
  sondern der Beleg dafür, dass sauber geprüft wurde. Der Ton bleibt sachlich, nicht
  bedauernd.
- **Der letzte Satz ist die Pointe.** Danach nichts mehr sagen.
