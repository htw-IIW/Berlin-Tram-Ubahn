# src/analysis/grafiken.py
# Diagramme, die auch ausserhalb der Notebooks gebraucht werden.
#
# ── Warum dieses Modul existiert ─────────────────────────────────────────────
#
# Die Grafik "Verfruehung gegen Verspaetung" geht ins Video. Beschriftungen fuer
# ein Video werden erfahrungsgemaess mehrfach geaendert, und ein Notebook-Lauf
# dauert rund zehn Minuten. Die Zeichenlogik steht deshalb hier; das Notebook und
# scripts/grafik_richtungen.py rufen dieselbe Funktion auf.
#
# Damit bleibt es bei EINER Zeichenlogik — nur die Eintrittspunkte sind zwei. Das
# ist derselbe Grundsatz wie in scripts/export_grafiken.py: keine zweite,
# nachgebaute Fassung, die auseinanderlaufen kann.
#
# ── Beschriftungen aendern ───────────────────────────────────────────────────
#
# Alles, was im Bild als Text erscheint, steht unten im Block TEXTE. Danach:
#
#     python3 scripts/grafik_richtungen.py
#
# Das schreibt video/bild/richtungen_frueh_spaet.png in wenigen Sekunden neu,
# ohne ein Notebook zu rechnen.

import math
import re

import pandas as pd
import plotly.graph_objects as go

from src.analysis.quality import VERSPAETET_SCHWELLE_S


def fuers_video(fig: go.Figure) -> go.Figure:
    """Schriftgroessen fuer die Projektion anheben. Farben bleiben unberuehrt.

    Stand bis zum 09.08.2026 im PREAMBLE von scripts/export_grafiken.py und ist
    hierher gewandert, damit scripts/grafik_richtungen.py dieselbe Umrechnung
    benutzen kann statt einer zweiten, nachgebauten. Der Export ruft sie ueber
    einen verzoegerten Import auf — zum Zeitpunkt des ersten fig.show() liegt die
    Projektwurzel bereits im sys.path des Kernels.

    Wer hier Groessen aendert, aendert damit beide Wege gleichzeitig. Genau das
    ist der Zweck.
    """
    fig.update_layout(
        font=dict(size=19),
        title_font=dict(size=27),
        legend=dict(font=dict(size=17)),
        margin=dict(t=110, l=90, r=60, b=90),
    )
    for name in dir(fig.layout):
        if re.fullmatch(r"[xy]axis\d*", name):
            achse = getattr(fig.layout, name, None)
            if achse is not None:
                achse.update(title_font=dict(size=19), tickfont=dict(size=16))
    neu = []
    for ann in (fig.layout.annotations or []):
        ann.font.size = max(int(ann.font.size or 14) + 5, 19)
        neu.append(ann)
    if neu:
        fig.layout.annotations = neu
    return fig

# Ab wann eine Abfahrt als verfrueht gilt. Anders als VERSPAETET_SCHWELLE_S ist
# das keine zentrale Projektkonstante, weil nur die Verfruehungsanalyse sie
# braucht — der Wert steht deshalb hier und nicht in quality.py.
#
# ── Warum -120 und nicht -60 (geaendert am 10.08.2026) ───────────────────────
#
# Der BVG-Verkehrsvertrag zaehlt eine Abfahrt seit dem 01.01.2025 als unpuenktlich
# verfrueht, wenn sie **mehr als 60 Sekunden** vor der Fahrplanzeit stattfindet —
# also echt kleiner als -60. Weil delay_s minutenquantisiert ist (DATASET.md
# Nr. 1: alle Werte sind Vielfache von 60), ist der naechste moegliche Wert
# unterhalb von -60 genau -120:
#
#     mehr als 60 s zu frueh  ->  delay_s < -60  ->  delay_s <= -120
#
# -120 ist damit die woertliche Umsetzung der amtlichen Regel, keine Naeherung.
#
# Bis zum 10.08.2026 stand hier -60. Das war aus zwei Gruenden schlechter:
#
# 1. Es war STRENGER als der Vertrag, nicht lockerer — die Grenze schliesst den
#    Rasterwert -60 mit ein, den der Vertrag noch als puenktlich fuehrt.
# 2. Es war rundungsanfaellig. 45,8 % aller verfruehten Tram-Abfahrten liegen
#    exakt auf -60, und dieser eine Rasterwert kann eine echte Verfruehung von
#    wenigen Sekunden bedeuten. Fast die halbe Kennzahl haette damit an einer
#    Rundung gehangen, die aus den Daten nicht aufloesbar ist: `when` und
#    `planned_when` tragen ueber alle 13,2 Mio. Dokumente ausschliesslich die
#    Sekunde 0.
#
# Folgen der Umstellung, damit sie nicht ueberrascht: Der Anteil verfruehter
# Tram-Abfahrten faellt von 19,3 % auf 10,4 %, der der U-Bahn von 6,1 % auf
# 1,0 % — der Faktor zwischen den Netzen waechst dabei von 3,1 auf 10,4.
#
# Seit dem 10.08.2026 folgt auch die Gegenseite demselben Prinzip: Der Vertrag
# zaehlt ab mehr als 210 s, im Minutenraster ist das die Stufe 240 — sie steht
# fuer echte 210–270 s und deckt damit genau alles ab 210 ab. Die frueher
# benutzte 180 stand fuer echte 150–210 s, also fuer Fahrten INNERHALB des
# Fensters. Beide Schwellen bilden jetzt das Vertragsfenster ab, keine ist mehr
# eine eigene Setzung. Herleitung in quality.py bei VERSPAETET_SCHWELLE_S.
#
# Die Schwellen sind dabei zahlenmaessig weiterhin NICHT symmetrisch (-120 gegen
# +240) — sie sind es aber inhaltlich, weil der Vertrag selbst unsymmetrisch ist
# (60 s zu frueh gegen 210 s zu spaet). Die Begruendung fuer diese Asymmetrie
# steht in notebooks/01_eda.ipynb, Abschnitt 3b: Eine Verfruehung kostet den
# ganzen Takt, unabhaengig davon, wie gross sie ist — eine Verspaetung kostet nur
# ihre eigenen Minuten.
VERFRUEHT_SCHWELLE_S = -120

# Netzfarben wie im ganzen Projekt. Auf Farbfehlsichtigkeit geprueft:
# Abstand 26 (OKLab x100) unter Protanopie, 36 unter Tritanopie — beides weit
# ueber der Grenze von 8. Nicht gegen ein Rot/Gruen-Paar tauschen.
#
# ── Warum die Tram ROT ist und nicht orange (entschieden am 12.08.2026) ──────
#
# Erwogen wurde Dunkelorange, weil die Fahrzeuge selbst dunkelorange lackiert
# sind. Verworfen: Die BVG verwendet in ihrer eigenen Kommunikation Rot fuer die
# Strassenbahn, und daran haelt sich dieses Projekt. Die Entscheidung gilt fuer
# alle Grafiken und auch fuer kuenftige — wer eine neue Grafik baut, nimmt
# FARBE_NETZ und setzt keine eigene Farbe.
#
# Nebenwirkung, die dadurch vermieden bleibt: #E65100 (Dunkelorange) ist im
# Projekt bereits mit "zu spaet" belegt — im Tagesgang und auf den Karten. Waere
# die Tram orange geworden, haette dieselbe Farbe in einer Szene "Strassenbahn"
# und in der naechsten "Verspaetung" bedeutet.
FARBE_NETZ = {"Tram": "#E53935", "U-Bahn": "#1E88E5"}

# ── TEXTE ────────────────────────────────────────────────────────────────────
# Hier aendern. {minuten} und {netz}/{wert} werden eingesetzt.
TEXTE = {
    "titel": "Die Tram weicht in beide Richtungen häufiger ab",
    "untertitel": ("Anteil aller Abfahrten. Der pünktliche Rest — "
                   "Tram {p_tram} %, U-Bahn {p_ubahn} % — ist nicht dargestellt."),
    "kopf_links":  "◀  zu früh — mindestens {dauer}",
    "kopf_rechts": "zu spät — mindestens {dauer}  ▶",
    "faktor":      "Tram <b>{faktor}×</b> so oft wie die U-Bahn",
    "achse_x":     "Anteil der Abfahrten (%)",
}

# Rand der x-Achse in Prozentpunkten. Beide Seiten tragen denselben Massstab —
# eine asymmetrische Achse waere hier eine Luege, weil die Seiten verglichen
# werden sollen.
#
# None heisst: aus den Daten berechnen. Fest verdrahtet war der Wert 21, und das
# war ein Fehler — bei --spaet 60 reicht der laengste Balken auf 35,7 %, und
# plotly schneidet ihn am Achsenrand einfach ab, ohne zu warnen. Die Grafik sah
# dann richtig aus und war falsch. Eine Zahl hier eintragen nur, wenn man den
# Ausschnitt bewusst erzwingen will, und dann das Ergebnis ansehen.
GRENZE_PCT = None


def _de(x, n=1):
    """Deutsches Dezimalkomma — die Grafik geht so ins Video."""
    return f"{x:.{n}f}".replace(".", ",")


def _dauer(sekunden: int) -> str:
    """„1 Minute" / „3 Minuten" — sonst steht im Bild „mindestens 1 Minuten".

    Halbe Minuten bekommen ihr Bruchzeichen: 210 s ist die amtliche
    Verspaetungsgrenze und heisst im Film „dreieinhalb Minuten", nicht „drei".
    """
    minuten, rest = divmod(abs(sekunden), 60)
    if rest == 30:
        return f"{minuten}½ Minuten"
    return f"{minuten} Minute" if minuten == 1 else f"{minuten} Minuten"


def anteile_pro_richtung(
    es,
    schwelle_frueh_s: int = VERFRUEHT_SCHWELLE_S,
    schwelle_spaet_s: int = VERSPAETET_SCHWELLE_S,
    indizes=(("Tram", "tram-departures-v2"), ("U-Bahn", "ubahn-departures-v2")),
) -> pd.DataFrame:
    """Anteil zu frueher, puenktlicher und zu spaeter Abfahrten je Netz.

    Rueckgabe: eine Zeile je Netz mit `zu früh (%)`, `pünktlich (%)`,
    `zu spät (%)` und `n`.
    """
    zeilen = []
    for netz, index in indizes:
        antwort = es.search(
            index=index, size=0, query={"exists": {"field": "delay_s"}},
            aggs={
                "zu_frueh": {"filter": {"range": {"delay_s": {"lte": schwelle_frueh_s}}}},
                "puenktlich": {"filter": {"range": {"delay_s": {"gt": schwelle_frueh_s,
                                                               "lt": schwelle_spaet_s}}}},
                "zu_spaet": {"filter": {"range": {"delay_s": {"gte": schwelle_spaet_s}}}},
            },
        )
        n = es.count(index=index, query={"exists": {"field": "delay_s"}})["count"]
        a = antwort["aggregations"]
        zeilen.append({
            "Netz": netz, "n": n,
            "zu früh (%)": a["zu_frueh"]["doc_count"] / n * 100,
            "pünktlich (%)": a["puenktlich"]["doc_count"] / n * 100,
            "zu spät (%)": a["zu_spaet"]["doc_count"] / n * 100,
        })
    return pd.DataFrame(zeilen)


def richtungsvergleich(
    anteile: pd.DataFrame,
    schwelle_frueh_s: int = VERFRUEHT_SCHWELLE_S,
    schwelle_spaet_s: int = VERSPAETET_SCHWELLE_S,
) -> go.Figure:
    """Verfruehungen und Verspaetungen an einer gemeinsamen Nulllinie.

    Der puenktliche Rest bleibt weg. Im gestapelten Balken (01_eda, Abschnitt 3b)
    erdrueckt er mit 70 bzw. 90 Prozent genau die beiden Anteile, um die es geht.

    Die Schwellen werden mituebergeben, damit die Kopfzeilen nicht von den Daten
    abweichen koennen: Wer die Schwelle aendert, aendert automatisch die
    Beschriftung mit.
    """
    reihenfolge = ["U-Bahn", "Tram"]          # Tram oben
    werte = anteile.set_index("Netz").loc[reihenfolge]
    farben = [FARBE_NETZ[netz] for netz in reihenfolge]

    # Achsenrand so, dass der laengste Balken sicher hineinpasst.
    grenze = GRENZE_PCT
    if grenze is None:
        groesster = max(werte["zu früh (%)"].max(), werte["zu spät (%)"].max())
        grenze = max(5.0, math.ceil(groesster * 1.12 / 5) * 5)
    schritt = 5 if grenze <= 25 else 10
    ticks = [t for t in range(-int(grenze), int(grenze) + 1, schritt)]

    # Ein Balken muss breit genug sein, damit die Beschriftung hineinpasst.
    # Bei der U-Bahn und der Zwei-Minuten-Schwelle sind es 1,0 % — der Balken ist
    # dann schmaler als der Text "1,0 %", und plotly setzt ihn trotzdem hinein,
    # wo er links und rechts ueberlaeuft. Unterhalb dieses Anteils der Achse
    # wandert die Zahl deshalb nach aussen und wechselt die Schriftfarbe.
    MINDESTBREITE = 0.10

    fig = go.Figure()
    for spalte, vorzeichen, richtung in [("zu früh (%)", -1, "zu früh"),
                                         ("zu spät (%)", +1, "zu spät")]:
        innen = [v / grenze >= MINDESTBREITE for v in werte[spalte]]
        fig.add_trace(go.Bar(
            y=reihenfolge, x=vorzeichen * werte[spalte], orientation="h",
            width=0.52, marker_color=farben, showlegend=False,
            text=[f"{_de(v)} %" for v in werte[spalte]],
            textposition=["inside" if i else "outside" for i in innen],
            insidetextanchor="middle",
            textfont=dict(size=15,
                          color=["white" if i else "#424242" for i in innen]),
            cliponaxis=False,
            hovertemplate="%{y}: %{text} " + richtung + "<extra></extra>",
        ))

    fig.add_vline(x=0, line_width=1, line_color="#9e9e9e")

    faktoren = {
        -1: werte.loc["Tram", "zu früh (%)"] / werte.loc["U-Bahn", "zu früh (%)"],
        +1: werte.loc["Tram", "zu spät (%)"] / werte.loc["U-Bahn", "zu spät (%)"],
    }
    koepfe = {
        -1: TEXTE["kopf_links"].format(dauer=_dauer(schwelle_frueh_s)),
        +1: TEXTE["kopf_rechts"].format(dauer=_dauer(schwelle_spaet_s)),
    }
    for seite in (-1, +1):
        x_pos = seite * grenze * 0.5
        fig.add_annotation(x=x_pos, y=1.80, text=f"<b>{koepfe[seite]}</b>",
                           showarrow=False, xanchor="center",
                           font=dict(size=14, color="#424242"))
        fig.add_annotation(x=x_pos, y=-0.78, showarrow=False, xanchor="center",
                           text=TEXTE["faktor"].format(faktor=_de(faktoren[seite])),
                           font=dict(size=13, color="#616161"))

    untertitel = TEXTE["untertitel"].format(
        p_tram=_de(werte.loc["Tram", "pünktlich (%)"], 0),
        p_ubahn=_de(werte.loc["U-Bahn", "pünktlich (%)"], 0),
    )
    fig.update_layout(
        barmode="overlay",
        title=f"{TEXTE['titel']}<br><sub>{untertitel}</sub>",
        xaxis=dict(title=TEXTE["achse_x"], range=[-grenze, grenze],
                   tickvals=ticks, ticktext=[str(abs(t)) for t in ticks],
                   zeroline=False, gridcolor="#eeeeee"),
        yaxis=dict(title="", categoryorder="array", categoryarray=reihenfolge,
                   range=[-1.35, 2.45], showgrid=False),
        plot_bgcolor="white", height=430,
    )
    return fig


# ── Dieselbe Grafik, in der Mitte aufgeteilt ─────────────────────────────────
#
# richtungsvergleich() zeigt beide Richtungen gleichzeitig. Fuer den Film wird
# sie an der Nulllinie zerlegt: In Szene 5 laeuft nur die Verspaetungsseite, die
# Verfruehungsseite kommt erst in Szene 8. Der Zuschauer sieht die zweite Haelfte
# also, nachdem er die erste fuer das ganze Bild gehalten hat.
#
# ── Der Massstab ist die ganze Grafik ────────────────────────────────────────
#
# Beide Haelften MUESSEN dieselbe x-Achse tragen. Rechnet man den Achsenrand je
# Bild neu, wird der laengste Balken jedes Mal gleich lang — 6,2 % in Szene 5
# saehen aus wie 10,5 % in Szene 8, und die Pointe waere zerstoert, bevor sie
# ausgesprochen ist. Deshalb nimmt `grenze` beide Richtungen entgegen; wer nur
# eine Haelfte zeichnet, muss den Wert von aussen setzen.
# scripts/grafik_richtung_halb.py tut genau das und schreibt darum beide Bilder
# in einem Lauf — getrennt aufgerufen koennten sie auseinanderlaufen.
#
# ── Warum die Verfruehungsseite nach links zeigt ─────────────────────────────
#
# Sie behaelt die Richtung, die sie in der vollen Grafik hat: zu frueh nach
# links, zu spaet nach rechts, wie auf einem Zeitstrahl. Damit lassen sich die
# beiden Bilder im Schnitt auch nebeneinanderlegen und ergeben wieder das Ganze.
# Bei der linken Haelfte wandert die Netzbeschriftung auf die rechte Seite, weil
# die Balken dort an der Nulllinie beginnen.

# Ohne Titel und ohne Untertitel — der Titel wird im Schnitt gesetzt. Das Bild
# traegt nur noch die Kopfzeile, die Netznamen, die Werte und die Achse.
TEXTE_HALB = {
    "spaet": {"kopf": "zu spät  {dauer}  ▶"},
    "frueh": {"kopf": "◀  zu früh  {dauer}"},
    "achse_x": "Anteil der Abfahrten (%)",
}

# ── Warum im Bild andere Minuten stehen als im Filter ────────────────────────
#
# Gefiltert wird auf delay_s <= -120 und delay_s >= 240. Waeren diese Zahlen die
# Beschriftung, stuende im Bild "mindestens 2 Minuten" und "mindestens 4
# Minuten" — und der Sprechtext sagt im selben Moment "hoechstens dreieinhalb
# Minuten zu spaet" (Szene 2) und "mehr als eine Minute vor der Fahrplanzeit"
# (Szene 8). Zwei verschiedene Zahlen fuer dieselbe Sache, eine gesprochen und
# eine im Bild: Der Zuschauer haelt eine davon fuer falsch.
#
# Richtig ist beides. Der Vertrag zieht die Grenze bei 60 s zu frueh und 210 s zu
# spaet; delay_s ist minutenquantisiert (DATASET.md Nr. 1), der naechste
# moegliche Wert jenseits der Grenze ist deshalb -120 bzw. 240. Herleitung im
# Kopf von VERFRUEHT_SCHWELLE_S.
#
# Im Bild steht die VERTRAGSREGEL, weil sie das ist, was gesprochen wird. Fuer
# andere Schwellen als die beiden vertraglichen gibt es keine solche Regel — dann
# faellt die Beschriftung auf den gefilterten Wert zurueck.
VERTRAGSTEXT = {240: "mehr als 3½ Minuten", -120: "mehr als 1 Minute"}


def _fenstertext(schwelle_s: int) -> str:
    return VERTRAGSTEXT.get(schwelle_s, f"mindestens {_dauer(schwelle_s)}")


def richtungsvergleich_halb(
    anteile: pd.DataFrame,
    richtung: str = "spaet",
    schwelle_s: int | None = None,
    grenze: float | None = None,
) -> go.Figure:
    """Eine Haelfte von `richtungsvergleich` — nur zu spaet oder nur zu frueh.

    `richtung` ist "spaet" oder "frueh". `grenze` ist der Achsenrand in Prozent;
    ohne Angabe wird er aus BEIDEN Richtungen berechnet, damit die zwei Bilder
    auch bei getrenntem Aufruf denselben Massstab tragen.
    """
    if richtung not in ("spaet", "frueh"):
        raise ValueError(f"richtung ist 'spaet' oder 'frueh', nicht {richtung!r}")

    spalte = "zu spät (%)" if richtung == "spaet" else "zu früh (%)"
    vorzeichen = +1 if richtung == "spaet" else -1
    if schwelle_s is None:
        schwelle_s = (VERSPAETET_SCHWELLE_S if richtung == "spaet"
                      else VERFRUEHT_SCHWELLE_S)

    reihenfolge = ["U-Bahn", "Tram"]          # Tram oben, wie in der vollen Grafik
    werte = anteile.set_index("Netz").loc[reihenfolge]
    farben = [FARBE_NETZ[netz] for netz in reihenfolge]

    if grenze is None:
        grenze = achsenrand(anteile)
    schritt = 2 if grenze <= 14 else 5
    ticks = [vorzeichen * t for t in range(0, int(grenze) + 1, schritt)]

    # Begruendung siehe richtungsvergleich(): schmale Balken fassen ihre
    # Beschriftung nicht, die Zahl muss dann nach aussen. Die Schrift ist hier
    # groesser als in der vollen Grafik — es sind nur zwei Balken statt vier,
    # und das Bild laeuft im Video als Vollformat.
    MINDESTBREITE = 0.12
    innen = [v / grenze >= MINDESTBREITE for v in werte[spalte]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=reihenfolge, x=vorzeichen * werte[spalte], orientation="h",
        width=0.46, marker_color=farben, showlegend=False,
        text=[f"<b>{_de(v)} %</b>" for v in werte[spalte]],
        textposition=["inside" if i else "outside" for i in innen],
        insidetextanchor="middle",
        textfont=dict(size=26,
                      color=["white" if i else "#424242" for i in innen]),
        cliponaxis=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color="#9e9e9e")

    # Die Kopfzeile sitzt an der Nulllinie und laeuft in die Richtung, in die
    # auch die Balken wachsen. In der Bildmitte (wie in der vollen Grafik) haette
    # sie hier ueber leerer Flaeche gestanden, weil die zweite Haelfte fehlt.
    fig.add_annotation(
        x=0, y=1.58, showarrow=False, xshift=vorzeichen * 8,
        xanchor="left" if vorzeichen > 0 else "right",
        text="<b>"
             + TEXTE_HALB[richtung]["kopf"].format(dauer=_fenstertext(schwelle_s))
             + "</b>",
        font=dict(size=16, color="#424242"))

    achse = [0, grenze] if vorzeichen > 0 else [-grenze, 0]
    fig.update_layout(
        title=None,
        xaxis=dict(title=TEXTE_HALB["achse_x"], range=achse,
                   tickvals=ticks, ticktext=[str(abs(t)) for t in ticks],
                   zeroline=False, gridcolor="#eeeeee"),
        # Bei der linken Haelfte steht die Nulllinie rechts — die Netznamen
        # gehoeren dorthin, wo die Balken anfangen.
        #
        # Die y-Grenzen sind knapper als in der vollen Grafik: Dort steht unter
        # jeder Seite noch eine Faktorzeile, hier traegt der Titel den Faktor.
        # Mit dem alten Bereich haetten zwei Balken 1080 Pixel Hoehe gefuellt und
        # ringsum nur Weiss gestanden.
        yaxis=dict(title="", categoryorder="array", categoryarray=reihenfolge,
                   range=[-0.62, 1.88], showgrid=False,
                   side="left" if vorzeichen > 0 else "right"),
        plot_bgcolor="white", height=430,
    )
    return fig


def achsenrand(anteile: pd.DataFrame, raster: int = 2) -> float:
    """Gemeinsamer Achsenrand fuer beide Haelften, in Prozent.

    `raster` ist die Schrittweite, auf die aufgerundet wird. Die volle Grafik
    rundet auf 5 — bei 10,45 % als groesstem Wert kommt dabei 15 heraus, und der
    laengste Balken fuellt nur zwei Drittel der Achse. In der halben Grafik faellt
    das staerker auf, weil die Gegenseite fehlt; mit `raster=2` wird daraus 12.
    Der Massstab bleibt fuer beide Haelften derselbe, nur enger gefasst.
    """
    groesster = max(anteile["zu früh (%)"].max(), anteile["zu spät (%)"].max())
    return max(float(raster), math.ceil(groesster * 1.06 / raster) * raster)


# ── Validierung: eigene Messung gegen Qualitaetsmonitor ──────────────────────
#
# Wozu die Grafik da ist: Sie belegt, dass die eigene Erhebung dasselbe misst wie
# die Senatsverwaltung.
#
# ── Warum Tram gegen U-Bahn und nicht der Abstand ────────────────────────────
#
# Die erste Fassung zeigte den ABSTAND zwischen den Netzen als Balken (12,9 pp
# gegen 11,1 pp). Formal richtig und im Video unbrauchbar: "Abstand in
# Prozentpunkten" ist eine abgeleitete Groesse, die niemand in der einen Sekunde
# liest, die ein Videobild hat. Verworfen am 12.08.2026.
#
# Diese Fassung zeigt vier Balken je Kennzahl — Tram und U-Bahn, einmal aus der
# eigenen Erhebung und einmal aus dem Monitor. Die Aussage steht damit in der
# FORM und nicht in einer Zahl: links und rechts dasselbe Bild. Der Zuschauer
# muss nichts rechnen.
#
# ── Warum die negativ gewendeten Kennzahlen ──────────────────────────────────
#
# Gezeigt wird "ausserhalb des Puenktlichkeitsfensters" statt "puenktlich" und
# "ausgefallen" statt "Zuverlaessigkeit". Zwei Gruende:
#
# 1. In der positiven Fassung liegen alle vier Balken zwischen 84 und 99 %. Die
#    Unterschiede verschwinden optisch, und die einzige Rettung waere eine bei
#    85 % beginnende Achse. Die ist bei Balken verboten — die Laenge steht dann
#    fuer nichts mehr.
# 2. Negativ gewendet sind es Faktoren statt Nachkommastellen: Die Tram liegt
#    rund sechsmal so oft ausserhalb des Fensters. Dieselbe Zahl, nur sichtbar.
#
# ── Die Niveaus stimmen nicht ueberein, und das ist in Ordnung ───────────────
#
# Der Monitor zaehlt je FAHRT, diese Erhebung je ABFAHRT AN EINER HALTESTELLE.
# Die eigene Unpuenktlichkeitsquote liegt deshalb systematisch HOEHER (Mai 2026:
# 15,6 % gegen 13,1 % bei der Tram). Das Bild behauptet auch nichts anderes: Die
# Aussage ist "dasselbe Muster", nicht "dieselben Zahlen". Im Sprechtext ist die
# Zaehleinheit unmittelbar davor erklaert; der Untertitel wiederholt sie.
#
# Farben: die Netzfarben des Projekts, weil hier tatsaechlich Tram gegen U-Bahn
# steht — anders als in der verworfenen Abstandsfassung, die zwei Quellen
# gegeneinandergestellt hat. Pruefung siehe FARBE_NETZ.

TEXTE_VALIDIERUNG = {
    "titel": "Vergleich: amtliche vs. selbst erhobene Daten",
    # Kein Satz mehr zur Zaehleinheit. Er behauptete eine Erklaerung fuer den
    # Niveauunterschied, die sich am 17.08.2026 nicht halten liess.
    "untertitel": ("{monat}. Links der Qualitätsmonitor der Senatsverwaltung, "
                   "rechts meine Erhebung aus der öffentlichen "
                   "Abfahrts-API."),

    # ACHTUNG, zwei verschiedene Dinge:
    #
    # `quellen` sind die SCHLUESSEL in der Spalte `Quelle` des DataFrames. Sie
    # sind der Vertrag mit scripts/grafik_validierung.py — wer sie aendert, muss
    # dort mitaendern, sonst bricht der Zugriff mit einem KeyError ab.
    #
    # `beschriftung` ist der Text, der im BILD unter den Balken steht. Hier
    # gefahrlos aendern; die Zuordnung laeuft ueber den Schluessel links.
    "quellen": ["amtlich", "meine Messung"],
    # Welche Quelle hervorgehoben wird — voll gesaettigt statt blass. Haengt
    # am NAMEN und nicht an der Position, sonst kippt die Hervorhebung mit,
    # sobald jemand die Reihenfolge in `quellen` aendert.
    "hervorgehoben": "meine Messung",
    "beschriftung": {
        "meine Messung": "meine Messung",
        "amtlich": "amtliche Messung",
    },
    "faktor": "Tram {faktor}×",
}

# Je Kennzahl der Titel der Facette. Die Reihenfolge im DataFrame bestimmt, was
# links und was rechts steht.
TITEL_VALIDIERUNG = {
    "unpünktlich": "Außerhalb des Pünktlichkeitsfensters",
    "ausgefallen": "Ausgefallene Fahrten",
}


# ── Zwei grosse Zahlen: der Mittelwert je Netz ───────────────────────────────
#
# Fuer Szene 4. Ein Diagramm waere hier falsch: Es gibt nur zwei Werte, und die
# Aussage ist, dass sie NAH BEIEINANDER liegen. Zwei Balken zu diesen Zahlen
# haetten eine sichtbare Laengendifferenz und wuerden genau das Gegenteil
# behaupten. Grosse Zahlen sind die richtige Form — im Video ausserdem die
# einzige, die auf einem Beamer aus der letzten Reihe lesbar ist.
#
# Warum nicht die Kibana-Kacheln: Die koennen es auch, aber nur als ZWEI Panels.
# Sobald eine Lens-Metric einen Breakdown bekommt, teilen sich alle Kacheln
# dieselbe statische Farbe — Rot und Blau nebeneinander ist dort nicht
# einstellbar. Diese Fassung ist eine Datei und trifft die Netzfarben exakt.

TEXTE_KACHELN = {
    "titel": "Im Mittel trennen beide Netze zehn Sekunden",
    "untertitel": ("Mittlere Abweichung von der Fahrplanzeit je Abfahrt, "
                   "{zeitraum}. Positiv heißt zu spät."),
    "fussnote": "Der Mittelwert allein trägt diesen Vergleich nicht.",
}


def kennzahl_kacheln(werte: dict, zeitraum: str = "",
                     einheit: str = " s") -> go.Figure:
    """Je Netz eine grosse Zahl nebeneinander.

    `werte` ist ein Dictionary `{"Tram": 33.0, "U-Bahn": 22.5}`. Gerundet wird
    auf ganze Einheiten — die Nachkommastelle traegt im Video nichts und die
    Erhebung laeuft ohnehin weiter.
    """
    netze = list(werte)
    fig = go.Figure()

    # Kein Achsensystem, keine Balken — nur Text auf leerer Flaeche. Die
    # Positionen sind Papierkoordinaten, damit sie nicht von Daten abhaengen.
    # xanchor ausdruecklich auf "center". Ohne das setzt plotly den Anker je
    # nach Position automatisch, und die Beschriftung stand nicht mittig unter
    # ihrer Zahl — bei 150 px Schrift faellt das sofort auf.
    for nr, netz in enumerate(netze):
        mitte = (nr + 0.5) / len(netze)
        fig.add_annotation(
            x=mitte, y=0.66, xref="paper", yref="paper", showarrow=False,
            xanchor="center", yanchor="middle",
            text=f"<b>{round(werte[netz]):.0f}{einheit}</b>",
            font=dict(size=140, color=FARBE_NETZ[netz]))
        fig.add_annotation(
            x=mitte, y=0.34, xref="paper", yref="paper", showarrow=False,
            xanchor="center", yanchor="middle",
            text=netz, font=dict(size=44, color="#37474F"))

    fig.add_annotation(
        x=0.5, y=0.05, xref="paper", yref="paper", showarrow=False,
        xanchor="center", yanchor="middle",
        text=TEXTE_KACHELN["fussnote"],
        font=dict(size=26, color="#90A4AE"))

    fig.update_layout(
        title=dict(text=(f"<b>{TEXTE_KACHELN['titel']}</b><br>"
                         f"<span style='font-size:22px;color:#616161'>"
                         f"{TEXTE_KACHELN['untertitel'].format(zeitraum=zeitraum)}"
                         f"</span>"),
                   x=0.5, xanchor="center", y=0.95, yanchor="top"),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=190, l=60, r=60, b=60), height=470,
    )
    return fig


# ── Dieselbe Aussage als Klickanimation ──────────────────────────────────────
#
# Fuer den Videoschnitt: Das Bild beginnt weiss und baut sich auf Klick auf. Der
# Grund ist dramaturgisch — wer vier Balken gleichzeitig sieht, liest sie in
# beliebiger Reihenfolge; wer sie nacheinander sieht, folgt dem Satz, der gerade
# gesprochen wird.
#
# Die amtlichen Balken sind blass, die eigenen voll gesaettigt. Das ist Absicht:
# Die eigene Messung ist die Aussage, die amtliche ist die Bestaetigung. Beide
# behalten aber ihre Netzfarbe — ein grauer Balken wuerde die Zuordnung Tram /
# U-Bahn zerstoeren, die im ganzen Video an Rot und Blau haengt.
#
# Nur die PUENKTLICHKEIT. Die Ausfaelle sind an dieser Stelle der Storyline noch
# nicht eingefuehrt und wuerden ablenken (Entscheidung vom 12.08.2026). Die
# Zeichenlogik kann sie — es wird nur eine Kennzahl uebergeben.

TEXTE_ANIMATION = {
    "titel": "Vergleich: amtliche vs. selbst erhobene Daten",
    # Nennt die beiden QUELLEN, nicht die Zaehleinheit — der Vergleich ist
    # "direkt von der BVG" gegen "oeffentliche API", und mehr ist belegbar.
    "hinweis": ("Der Qualitätsmonitor bekommt die Daten <b>direkt von der BVG</b> — ich messe über die <b>öffentliche Abfahrts-API</b>."),
    "achse_y": "Anteil der Abfahrten außerhalb des Pünktlichkeitsfensters",
    "achse_y_spaet": "Anteil der Abfahrten mehr als 3½ Minuten zu spät",
    "differenz": "Differenz:",
}

# Die Raender der Zeichenflaeche in Pixeln. Sie stehen hier und nicht nur im
# Layout, weil scripts/animation_validierung.py dieselben Werte fuer das CSS der
# Differenzzeile braucht — nur so steht jede Zahl mittig unter ihrer Gruppe.
RAND_LINKS, RAND_RECHTS, RAND_UNTEN = 130, 260, 200

# Wie blass die amtlichen Balken werden. 0.30 ist geprueft: deutlich zurueck-
# tretend, aber die Farbe bleibt als Tram/U-Bahn erkennbar.
DECKKRAFT_AMTLICH = 0.30


def _rgba(hexwert: str, alpha: float) -> str:
    h = hexwert.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def validierung_animation(werte: pd.DataFrame, kennzahl: str = "unpünktlich"):
    """Figur und Klickschritte für die Aufbau-Animation.

    Rueckgabe: `(fig, schritte)`. `schritte` ist eine Liste von Dictionaries, die
    das HTML-Skript nacheinander an `Plotly.update` weiterreicht — Schritt fuer
    Schritt, jeweils auf Klick. Der Nullzustand ist bereits in `fig` gesetzt:
    leere Balken, unsichtbare Beschriftungen.
    """
    quellen = TEXTE_VALIDIERUNG["quellen"]
    beschriftet = [TEXTE_VALIDIERUNG["beschriftung"].get(q, q) for q in quellen]
    tabelle = werte[werte["Kennzahl"] == kennzahl].set_index("Quelle")
    if not all(q in tabelle.index for q in quellen):
        raise KeyError(f"Kennzahl {kennzahl!r} hat nicht beide Quellen "
                       f"{quellen} — vorhanden: {list(tabelle.index)}")

    hoehen = {netz: [tabelle.loc[q, netz] for q in quellen]
              for netz in ("Tram", "U-Bahn")}

    fig = go.Figure()
    for netz in ("Tram", "U-Bahn"):
        fig.add_trace(go.Bar(
            x=beschriftet, y=[None, None], name=netz, width=0.30,
            # Erster Eintrag voll, zweiter blass — die Reihenfolge folgt
            # `quellen`, also eigene Messung zuerst.
            marker_color=[
                FARBE_NETZ[netz] if q == TEXTE_VALIDIERUNG["hervorgehoben"]
                else _rgba(FARBE_NETZ[netz], DECKKRAFT_AMTLICH)
                for q in quellen],
            text=["", ""], textposition="outside", cliponaxis=False,
            textfont=dict(size=26, color="#424242"),
            hovertemplate=f"{netz}, %{{x}}: %{{y:.2f}} %<extra></extra>",
        ))

    beschriftungen = {netz: [f"{_de(h)} %" for h in hoehen[netz]]
                      for netz in hoehen}
    hoechster = max(max(h) for h in hoehen.values())

    fig.update_layout(
        # Titel und Hinweis sind Annotationen statt layout.title, damit beide
        # ueber denselben Weg ein- und ausgeblendet werden koennen.
        # Reihenfolge ist verbindlich — das HTML-Skript spricht die Annotationen
        # ueber ihren Index an: 0 Titel, 1 Hinweis. Mehr sind es nicht.
        #
        # Die Differenzen stehen bewusst NICHT hier. Als Annotation unterhalb der
        # Achse sind sie mit den Achsenbeschriftungen kollidiert, sobald plotly
        # die Kategorien schraeg stellt — im Video sah es aus wie ein Textfehler.
        # Sie liegen jetzt als eigenes HTML-Element unter der Grafik, siehe
        # scripts/animation_validierung.py.
        annotations=[
            dict(x=0, y=1.16, xref="paper", yref="paper", xanchor="left",
                 text=f"<b>{TEXTE_ANIMATION['titel']}</b>", showarrow=False,
                 font=dict(size=36, color="#1A3A5C"), visible=False),
            dict(x=0, y=1.05, xref="paper", yref="paper", xanchor="left",
                 text=TEXTE_ANIMATION["hinweis"], showarrow=False,
                 font=dict(size=25, color="#616161"), visible=False),
        ],
        # tickangle ausdruecklich auf 0: Sonst dreht plotly die Kategorien in
        # schmalen Fenstern auf 45 Grad, und die Ausrichtung der Differenzzeile
        # darunter stimmt nicht mehr.
        xaxis=dict(categoryorder="array", categoryarray=beschriftet,
                   showgrid=False, tickangle=0,
                   tickfont=dict(size=30, color="#37474F")),
        # Feste Achse ab dem ersten Balken — ohne sie springt der Massstab beim
        # zweiten Klick, und die Balken der eigenen Messung schrumpfen im Bild,
        # obwohl sich an ihrem Wert nichts geaendert hat.
        yaxis=dict(title=dict(text=TEXTE_ANIMATION["achse_y"],
                              font=dict(size=22, color="#616161")),
                   range=[0, hoechster * 1.22], gridcolor="#ECEFF1",
                   zeroline=False, ticksuffix=" %",
                   tickfont=dict(size=24, color="#37474F")),
        separators=",.",
        barmode="group", bargroupgap=0.10,
        legend=dict(font=dict(size=30), x=1.01, xanchor="left",
                    y=1.0, yanchor="top", bgcolor="rgba(0,0,0,0)"),
        plot_bgcolor="white", paper_bgcolor="white",
        # Der untere Rand traegt die Achsenbeschriftung UND darunter die
        # Differenzzeile aus dem HTML. Wer ihn verkleinert, muss RAND_UNTEN in
        # scripts/animation_validierung.py mitziehen, sonst ueberlappt beides.
        margin=dict(t=190, l=RAND_LINKS, r=RAND_RECHTS, b=RAND_UNTEN),
    )

    # Ein Schritt = ein Klick. Zwei Arten:
    #
    #   {"layout": {...}}  geht unveraendert an Plotly.relayout — Ein- und
    #                      Ausblenden von Titel und Hinweis.
    #   {"balken": {...}}  laesst das HTML-Skript die beiden Balken einer Quelle
    #                      GEMEINSAM von null auf ihren Wert hochfahren und
    #                      setzt die Prozentzahl erst danach. `i` ist die
    #                      Position auf der x-Achse, `y` und `text` folgen der
    #                      Reihenfolge der Traces (erst Tram, dann U-Bahn).
    #
    # Warum Tram und U-Bahn gleichzeitig und nicht nacheinander: Die Aussage der
    # Szene ist das VERHAELTNIS der beiden. Wer sie nacheinander wachsen laesst,
    # laedt zum Lesen der Einzelwerte ein; wer sie zusammen wachsen laesst, zeigt
    # den Abstand.
    schritte = [
        {"layout": {"annotations[0].visible": True}},
        {"layout": {"annotations[1].visible": True}},
    ]
    for i in range(len(quellen)):
        schritte.append({"balken": {
            "i": i,
            "y": [hoehen["Tram"][i], hoehen["U-Bahn"][i]],
            "text": [beschriftungen["Tram"][i], beschriftungen["U-Bahn"][i]],
        }})

    # Letzter Klick: die Differenz je Quelle, als eigene Zeile unter der Grafik.
    #
    # Geschrieben als Prozentwert und nicht in Prozentpunkten. Fachlich ist die
    # Differenz zweier Anteile ein Prozentpunkt-Wert; im Video ist "pp" aber eine
    # Vokabel, die erklaert werden muesste, und dafuer ist keine Zeit. Wer genau
    # sein will, sagt beim Sprechen "dreizehn Prozentpunkte" — im Bild steht die
    # Zahl mit Prozentzeichen.
    schritte.append({"differenz": [
        _de(abs(hoehen["Tram"][i] - hoehen["U-Bahn"][i]), 1) + " %"
        for i in range(len(quellen))
    ]})
    return fig, schritte


def validierungsvergleich(werte: pd.DataFrame, monat: str = "") -> go.Figure:
    """Je Kennzahl vier Balken: Tram gegen U-Bahn, eigen gegen amtlich.

    `werte` braucht die Spalten `Kennzahl`, `Quelle`, `Tram` und `U-Bahn`. Die
    Zahlen sind Prozentanteile, bei denen NIEDRIGER BESSER ist — Anteil
    ausserhalb des Puenktlichkeitsfensters und Anteil ausgefallener Fahrten.
    Erwartet werden je Kennzahl zwei Zeilen, eine je Quelle.
    """
    from plotly.subplots import make_subplots

    kennzahlen = list(dict.fromkeys(werte["Kennzahl"]))
    quellen = TEXTE_VALIDIERUNG["quellen"]
    # Nachschlagen geschieht ueber `quellen`, angezeigt wird `beschriftet`.
    beschriftet = [TEXTE_VALIDIERUNG["beschriftung"].get(q, q) for q in quellen]
    tabelle = werte.set_index(["Kennzahl", "Quelle"])

    fehlend = [(k, q) for k in kennzahlen for q in quellen
               if (k, q) not in tabelle.index]
    if fehlend:
        raise KeyError(
            "Diese Kombinationen fehlen im DataFrame: "
            + ", ".join(f"{k}/{q}" for k, q in fehlend)
            + ". TEXTE_VALIDIERUNG['quellen'] muss zu den Werten in der Spalte "
              "`Quelle` passen — Anzeigetexte gehoeren in ['beschriftung'].")

    fig = make_subplots(
        rows=1, cols=len(kennzahlen), horizontal_spacing=0.14,
        subplot_titles=[f"<b>{TITEL_VALIDIERUNG[k]}</b>" for k in kennzahlen])

    for spalte, kennzahl in enumerate(kennzahlen, start=1):
        for netz in ("Tram", "U-Bahn"):
            hoehen = [tabelle.loc[(kennzahl, q), netz] for q in quellen]
            fig.add_trace(go.Bar(
                x=beschriftet, y=hoehen, name=netz, width=0.32,
                marker_color=FARBE_NETZ[netz],
                text=[f"{_de(h, 2 if h < 5 else 1)} %" for h in hoehen],
                textposition="outside", cliponaxis=False,
                textfont=dict(size=16, color="#424242"),
                # Nur die erste Facette speist die Legende, sonst stuende jedes
                # Netz doppelt darin.
                showlegend=(spalte == 1), legendgroup=netz,
                hovertemplate=f"{netz}, %{{x}}: %{{text}}<extra></extra>",
            ), row=1, col=spalte)

        hoechster = max(tabelle.loc[(kennzahl, q), netz]
                        for q in quellen for netz in ("Tram", "U-Bahn"))
        fig.update_yaxes(range=[0, hoechster * 1.30], gridcolor="#ECEFF1",
                         zeroline=False, ticksuffix=" %",
                         row=1, col=spalte)
        # tickangle=0, sonst dreht plotly die Kategorien in schmalen Fenstern
        # schraeg und laeuft in die Differenzzeile darunter.
        fig.update_xaxes(showgrid=False, tickangle=0, row=1, col=spalte)

        # Der Abstand zwischen den Netzen unter jede Quelle — gross und fett.
        # Das ist der eigentliche Beleg der Grafik: Die beiden Zahlen stehen
        # nebeneinander und sind fast gleich, waehrend die Balkenhoehen es nicht
        # sind. Wer nur auf die Balken sieht, liest den Niveauunterschied; wer
        # diese Zahlen liest, sieht die Uebereinstimmung.
        for i, q in enumerate(quellen):
            abstand = abs(tabelle.loc[(kennzahl, q), "Tram"]
                          - tabelle.loc[(kennzahl, q), "U-Bahn"])
            # "%" statt "pp": Fachlich ist die Differenz zweier Anteile ein
            # Prozentpunkt-Wert, aber "pp" muesste im Video erklaert werden.
            fig.add_annotation(
                x=i, y=0, yshift=-56, xref=f"x{spalte if spalte > 1 else ''}",
                yref=f"y{spalte if spalte > 1 else ''}",
                text=f"Differenz: <b>{_de(abstand, 1)} %</b>",
                showarrow=False, font=dict(size=21, color="#37474F"))

    for ann in fig.layout.annotations[:len(kennzahlen)]:   # die Facettentitel
        ann.update(font=dict(size=18, color="#37474F"))

    fig.update_layout(
        title=dict(text=(f"<b>{TEXTE_VALIDIERUNG['titel']}</b><br>"
                         f"<span style='font-size:14px;color:#616161'>"
                         f"{TEXTE_VALIDIERUNG['untertitel'].format(monat=monat)}"
                         f"</span>"),
                   x=0.01, xanchor="left", y=0.96, yanchor="top"),
        # separators setzt das Dezimalkomma auch auf den Achsenteilstrichen —
        # ohne das steht dort "0.5" statt "0,5".
        separators=",.",
        barmode="group", bargroupgap=0.10,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1.0),
        plot_bgcolor="white", height=470,
        margin=dict(t=185, l=90, r=60, b=110),
    )
    return fig


# ── Tagesgang: Verfruehung gegen Verspaetung ─────────────────────────────────
#
# Warum diese Grafik existiert: Die beiden Abweichungsrichtungen haben
# verschiedene Tageszeiten, und daraus folgen verschiedene Massnahmen. Die
# Verspaetung folgt dem Strassenverkehr, die Verfruehung der Nebenverkehrszeit.
# Eine gemeinsame Kennzahl ("Anteil ausserhalb des Fensters") wuerde beides
# vermischen und das Bild flach machen.
#
# Nur die Tram. Die U-Bahn liegt in beiden Richtungen unter 4 % und waere als
# dritte und vierte Linie nur Fuellung — der Netzvergleich ist an anderer Stelle
# schon gefuehrt. Vier Linien auf 24 Stuetzstellen sind im Video ohnehin nicht
# lesbar.
#
# Farben: dieselben wie auf den Karten (FARBE_FRUEH lila, FARBE_SPAET orange).
# Das ist Absicht — wer die Karte gesehen hat, liest die Linien ohne Legende.
# Geprueft mit scripts/validate_palette.js des dataviz-Skills: Abstand 28,7
# (OKLab x100) unter Protanopie, 26,2 unter Tritanopie, 32,6 bei normalem Sehen.
# Alle drei weit ueber der Grenze von 8.
#
# Bis zum 26.08.2026 war "zu frueh" tuerkis #0097A7. Wird hier umgefaerbt, muss
# karten.FARBE_FRUEH mit — sonst zeigen Karte und Tagesgang dieselbe Sache in
# zwei Farben, und der Verzicht auf eine Legende faellt in sich zusammen.
#
# ACHTUNG, anderer Filter als anteile_pro_richtung(): Hier wird das
# Analysefenster inklusive Collector-Ausfall angewandt. Bei einer Auswertung nach
# Tagesstunde ist das zwingend — waehrend des Ausfalls wurde unregelmaessig ueber
# den Tag abgetastet, einzelne Stunden waeren dadurch verzerrt. Die Fallzahl
# faellt dadurch von 11,4 auf 9,8 Mio.

FARBE_TAG_FRUEH = "#7B1FA2"   # identisch mit karten.FARBE_FRUEH
FARBE_TAG_SPAET = "#E65100"   # identisch mit karten.FARBE_SPAET

# ── Was die Daten hier sagen, und was sie NICHT sagen ────────────────────────
#
# Die naheliegende Erwartung war: Verspaetung folgt dem Berufsverkehr, hat also
# ihr Maximum am Nachmittag. Das stimmt fuer die Tram NICHT. Gemessen:
#
#   zu frueh  Maximum 15,3 % um 19 Uhr, Minimum  5,5 % um 22 Uhr
#   zu spaet  Maximum  9,9 % um 22 Uhr, Minimum  2,5 % um  5 Uhr
#
# Der Nachmittag ist zwar ein lokales Hoch (15/16 Uhr: 8,1 / 8,2 %), aber nicht
# das Maximum. Die Beschriftung darf deshalb nicht "am Nachmittag, mit dem
# Strassenverkehr" behaupten — das waere eine Ursachenaussage, die die Kurve
# nicht traegt.
#
# Der eigentliche Befund ist ein anderer und ein staerkerer: Die beiden Kurven
# laufen GEGENEINANDER. Spearman ueber alle 24 Stunden rho = -0,480 (p = 0,018),
# im Tagesverkehr 6-20 Uhr rho = -0,646 (p = 0,0092). Um 19 Uhr steht das
# Verfruehungsmaximum ueber dem niedrigsten Verspaetungswert des Abends, um
# 22 Uhr genau umgekehrt.
#
# Das ist die Signatur eines FAHRPLANS, dessen unterstellte Fahrzeiten je nach
# Tageszeit zu grosszuegig oder zu knapp sind — nicht die Signatur einer
# aeusseren Stoerung. Aeusserer Verkehr wuerde Verspaetung erzeugen, ohne die
# Verfruehung im selben Mass zu druecken. Genau darauf zielt die
# Handlungsempfehlung "realistische Fahrzeiten im Fahrplan".
#
# Zum Vergleich, weil es den Befund schaerft: Die U-BAHN zeigt das erwartete
# Muster — ihr Verspaetungsmaximum liegt um 16 Uhr (3,5 %), also im
# Berufsverkehr. Die Tram nicht.
TEXTE_TAGESGANG = {
    "frueh": "{netz} zu früh",
    "spaet": "{netz} zu spät",
    "fenster": "zu früh ab mehr als {frueh}, zu spät ab mehr als {spaet}",
    "achse_x": "Uhrzeit",
    "achse_y": "Anteil der Abfahrten (%)",
    "marke": "{stunde} Uhr {wert} %",
}


def tagesgang_anteile(
    es,
    index: str = "tram-departures-v2",
    schwelle_frueh_s: int = VERFRUEHT_SCHWELLE_S,
    schwelle_spaet_s: int = VERSPAETET_SCHWELLE_S,
    nur_werktage: bool = True,
) -> pd.DataFrame:
    """Anteil zu frueher und zu spaeter Abfahrten je Tagesstunde.

    Rueckgabe: eine Zeile je Stunde mit `stunde`, `n`, `zu früh (%)`,
    `zu spät (%)`.

    `nur_werktage` ist wie bei `tagesgang_netze_anteile()` die Vorgabe. Am
    Wochenende faehrt ein anderer Takt; wer den mit hineinrechnet, mittelt zwei
    Fahrplaene zu einer Kurve und redet trotzdem ueber den Berufsverkehr. Der
    Unterschied ist nicht klein: Um 19 Uhr faehrt die Tram werktags bei 16,5 %
    ihrer Abfahrten zu frueh, ueber alle Tage gerechnet bei 15,3 %.
    """
    from src.analysis.quality import analysefenster_query

    frage = analysefenster_query()
    frage["bool"].setdefault("filter", []).append({"exists": {"field": "delay_s"}})
    if nur_werktage:
        frage["bool"]["filter"].append({"term": {"is_weekend": False}})
    antwort = es.search(
        index=index, size=0, query=frage,
        aggs={"stunden": {
            "terms": {"field": "hour_of_day", "size": 24, "order": {"_key": "asc"}},
            "aggs": {
                "zu_frueh": {"filter": {"range": {"delay_s": {"lte": schwelle_frueh_s}}}},
                "zu_spaet": {"filter": {"range": {"delay_s": {"gte": schwelle_spaet_s}}}},
            },
        }},
    )
    zeilen = []
    for eimer in antwort["aggregations"]["stunden"]["buckets"]:
        n = eimer["doc_count"]
        zeilen.append({
            "stunde": eimer["key"], "n": n,
            "zu früh (%)": eimer["zu_frueh"]["doc_count"] / n * 100,
            "zu spät (%)": eimer["zu_spaet"]["doc_count"] / n * 100,
        })
    return pd.DataFrame(zeilen).sort_values("stunde").reset_index(drop=True)


def tagesgang(
    werte: pd.DataFrame,
    schwelle_frueh_s: int = VERFRUEHT_SCHWELLE_S,
    schwelle_spaet_s: int = VERSPAETET_SCHWELLE_S,
    netzname: str = "Tram",
    anzeige_frueh_s: int = -60,
    anzeige_spaet_s: int = 210,
) -> go.Figure:
    """Zwei Linien ueber 24 Stunden, gemeinsame Achse.

    Beide Reihen sind Anteile derselben Grundgesamtheit und teilen sich deshalb
    eine einzige y-Achse. Eine zweite Achse waere hier der klassische Fehler: Sie
    liesse den Massstab frei waehlbar und damit jede gewuenschte Kreuzung der
    beiden Linien erzeugen.

    ── Ohne Titel, mit zwei Marken ─────────────────────────────────────────

    Seit dem 21.08.2026 gebaut wie `tagesgang_netzvergleich()`: kein Titel und
    kein Untertitel, weil die Aussage im Film gesprochen wird und eine
    Bildueberschrift sie nur doppelt.

    Seit dem 26.08.2026 steht ueber dem Bild GAR NICHTS mehr. Die Fensterangabe
    ("zu frueh ab mehr als 1 Minute …") war als Ersatz an dieselbe Stelle
    gesetzt worden, an der zuvor der Untertitel stand — die Nutzerin hat beides
    entfernt. **Hier nichts wieder einsetzen.** Die Schwellen gehoeren in den
    Sprechtext, nicht ins Bild.

    Beschriftet werden die beiden Maxima, und zwar nur mit Uhrzeit und Wert.
    Der frueher hier stehende Deutungstext ("die meisten Verfruehungen — und
    zugleich wenig Verspaetung") nahm dem Sprechtext seinen Satz vorweg.

    ── Warum die Beschriftung andere Zahlen nennt als die Rechnung ─────────

    `schwelle_*_s` sind die Grenzen, mit denen gezaehlt wird (Projektfenster
    −120 s / +240 s). `anzeige_*_s` sind die Grenzen, die in der Beschriftung
    stehen (amtliches Fenster −60 s / +210 s). Beides bezeichnet dieselbe Menge
    von Abfahrten, weil `delay_s` in Minuten quantisiert ist: Zwischen -60 und
    -120 liegt kein Wert, zwischen 210 und 240 auch nicht. "Mehr als eine
    Minute zu frueh" ist deshalb genau `delay_s <= -120`.

    Wer die Anzeige auf -120 stellt, beschriftet die Grafik mit "mehr als zwei
    Minuten" und behauptet damit eine strengere Auswahl, als getroffen wurde.
    """
    fig = go.Figure()
    for spalte, farbe, muster in (
        ("zu früh (%)", FARBE_TAG_FRUEH, TEXTE_TAGESGANG["frueh"]),
        ("zu spät (%)", FARBE_TAG_SPAET, TEXTE_TAGESGANG["spaet"]),
    ):
        name = muster.format(netz=netzname)
        fig.add_trace(go.Scatter(
            x=werte["stunde"], y=werte[spalte], name=name,
            mode="lines", line=dict(color=farbe, width=3.5),
            hovertemplate=f"%{{x}} Uhr — {name} %{{y:.1f}} %<extra></extra>",
        ))

    # Direktbeschriftung am jeweiligen Maximum. Die Position kommt aus den Daten,
    # damit sie nicht stehen bleibt, wenn die Erhebung weiterlaeuft und das
    # Maximum auf eine andere Stunde wandert. Punkt plus Zahl wie im
    # Netzvergleich, damit beide Tagesgang-Grafiken des Films gleich aussehen.
    for spalte, farbe in (("zu früh (%)", FARBE_TAG_FRUEH),
                          ("zu spät (%)", FARBE_TAG_SPAET)):
        i = werte[spalte].idxmax()
        stunde, wert = int(werte.loc[i, "stunde"]), werte.loc[i, spalte]
        fig.add_trace(go.Scatter(
            x=[stunde], y=[wert], mode="markers", showlegend=False,
            marker=dict(color=farbe, size=16, line=dict(color="white", width=3)),
            hoverinfo="skip",
        ))
        fig.add_annotation(
            x=stunde, y=wert, showarrow=False, yshift=32, xanchor="center",
            text="<b>" + TEXTE_TAGESGANG["marke"].format(
                stunde=stunde, wert=_de(wert)) + "</b>",
            font=dict(size=18, color=farbe))

    # Kopfraum fuer die beiden Marken. Ohne ihn setzt plotly die Achse knapp
    # oberhalb des Maximums, und die obere Beschriftung wird am Rand abgeschnitten
    # — der Fehler faellt im PNG erst auf, wenn man es ansieht.
    hoechster = max(werte["zu früh (%)"].max(), werte["zu spät (%)"].max())

    # KEINE Kopfzeile ueber dem Bild. Untertitel und Fensterangabe sind von der
    # Nutzerin entfernt worden und bleiben entfernt — nichts an dieser Stelle
    # wieder einsetzen.
    fig.update_layout(
        xaxis=dict(title=TEXTE_TAGESGANG["achse_x"], dtick=2, showgrid=False,
                   ticksuffix=" h", zeroline=False),
        yaxis=dict(title=TEXTE_TAGESGANG["achse_y"], range=[0, hoechster * 1.22],
                   gridcolor="#ECEFF1", zeroline=False, ticksuffix=" %"),
        # Legende unten links im Bild: Der Bereich zwischen 0 und 8 Uhr liegt
        # unterhalb von 2,5 % und ist bei beiden Reihen frei.
        legend=dict(orientation="h", yanchor="bottom", y=0.02,
                    xanchor="left", x=0.01,
                    bgcolor="rgba(255,255,255,0.88)"),
        margin=dict(t=70),
        plot_bgcolor="white", height=470,
    )
    return fig


# ── Tagesgang der Verspätung, Tram gegen U-Bahn ──────────────────────────────
#
# Wozu die Grafik da ist: Sie prueft die naheliegendste Erklaerung fuer
# Verspaetung — den Berufsverkehr. Wenn volle Bahnen und langer Fahrgastwechsel
# die Ursache waeren, muesste das Maximum in der Hauptverkehrszeit liegen.
#
# Bei der U-Bahn tut es das (16 Uhr). Bei der Tram nicht: Sie hat zwar auch
# einen Nachmittagsgipfel, ihr Maximum liegt aber um 22 Uhr, wenn die Bahnen
# leer sind. Genau dort wechselt der Fahrplan vom 10- auf den 20-Minuten-Takt.
#
# ── Warum zwei Felder und nicht zwei Linien in einem ─────────────────────────
#
# Die Niveaus liegen um den Faktor 2,5 auseinander (Tram bis 9,9 %, U-Bahn bis
# 4,1 %). In einem gemeinsamen Feld mit gemeinsamer Achse waere die U-Bahn eine
# fast gerade Linie am unteren Rand, und ihr Nachmittagsgipfel — die halbe
# Aussage der Grafik — waere nicht mehr zu sehen. Zwei Achsen in EINEM Feld sind
# keine Option: Zwei verschiedene y-Skalen uebereinander sind der klassische
# Diagrammfehler, weil die Schnittpunkte der Linien dann etwas zu bedeuten
# scheinen. Zwei getrennte Felder sagen dasselbe ohne diese Falle.
#
# Damit die Niveaus trotzdem nicht verlorengehen, steht in jedem Feld der
# Tagesdurchschnitt des Netzes.
#
# ── Warum "Anteil zu spaet" und nicht der Mittelwert ─────────────────────────
#
# Der Mittelwert ueber alle Abfahrten verrechnet Verfruehung gegen Verspaetung.
# Um 19 Uhr faehrt die Tram so oft zu frueh, dass ihr Mittelwert auf 9,8 s
# faellt — die Kurve saehe dort nach einem Bestwert aus, obwohl 27,8 % der
# Abfahrten verspaetet sind. Der Anteil jenseits von VERSPAETET_SCHWELLE_S
# kennt dieses Problem nicht: Verfruehte Abfahrten zaehlen nicht mit und koennen
# nichts ausgleichen.

TEXTE_TAGESGANG_NETZE = {
    "achse_x": "Uhrzeit",
    "achse_y": "Anteil der Abfahrten mehr als 3½ Minuten zu spät",
    "hvz": "Rush Hour",
    "mittel": "Tagesmittel {wert} %",
    "gipfel": "{stunde} Uhr {wert} %",
}

# Die schattierten Baender. Kein amtlicher Begriff, sondern die Zeiten, in denen
# der Berufsverkehr in Berlin ueblicherweise liegt; sie sind das, wogegen die
# Grafik prueft.
HVZ_BAENDER = [(6.5, 9.5), (14.5, 18.5)]

# Erste Stunde des Betriebstags. Die Achse laeuft von hier 24 Stunden weiter,
# der Nachtverkehr steht damit am Ende statt am Anfang.
TAGESBEGINN = 4


INDIZES_NETZE = {"Tram": "tram-departures-v2", "U-Bahn": "ubahn-departures-v2"}
SPALTE_SPAET = "zu spät ≥240s (%)"


def tagesgang_netze_anteile(es, nur_werktage: bool = True) -> pd.DataFrame:
    """Anteil zu frueher und zu spaeter Abfahrten je Stunde und Netz.

    Eine Aggregation je Index. `nur_werktage` filtert auf `is_weekend: false` —
    am Wochenende gibt es keinen Berufsverkehr, gegen den sich pruefen liesse.

    Liegt hier und nicht im Skript, damit Notebook und
    scripts/grafik_tagesgang_netze.py dieselbe Abfrage benutzen.
    """
    from src.analysis.quality import VERSPAETET_SCHWELLE_S, analysefenster_query

    zeilen = []
    for netz, index in INDIZES_NETZE.items():
        frage = analysefenster_query()
        filter_ = frage["bool"].setdefault("filter", [])
        filter_.append({"exists": {"field": "delay_s"}})
        if nur_werktage:
            filter_.append({"term": {"is_weekend": False}})

        antwort = es.search(index=index, size=0, query=frage, aggs={"h": {
            "terms": {"field": "hour_of_day", "size": 24,
                      "order": {"_key": "asc"}},
            "aggs": {
                "spaet": {"filter": {"range": {"delay_s": {"gte": VERSPAETET_SCHWELLE_S}}}},
                "frueh": {"filter": {"range": {"delay_s": {"lte": VERFRUEHT_SCHWELLE_S}}}},
            }}})
        for eimer in antwort["aggregations"]["h"]["buckets"]:
            n = eimer["doc_count"]
            zeilen.append({
                "Netz": netz, "stunde": eimer["key"], "n": n,
                SPALTE_SPAET: eimer["spaet"]["doc_count"] / n * 100,
                "zu früh (%)": eimer["frueh"]["doc_count"] / n * 100,
            })
    return pd.DataFrame(zeilen)


def tagesgang_netzvergleich(werte: pd.DataFrame,
                            spalte: str = "zu spät ≥240s (%)") -> go.Figure:
    """Anteil verspaeteter Abfahrten je Stunde, beide Netze in EINEM Feld.

    `werte` braucht die Spalten `Netz`, `stunde`, `n` und `spalte` — so wie
    scripts/grafik_tagesgang_netze.py sie erzeugt.

    ── Ein Feld, nicht zwei ────────────────────────────────────────────────

    Bis zum 19.08.2026 lagen die Netze in zwei gestapelten Feldern mit je
    eigener Skala. Das war ein Fehler: Die U-Bahn-Kurve reichte dort ebenso
    hoch wie die Tram-Kurve, obwohl sie sich auf 4,1 statt 9,9 Prozent bezog.
    Wer die Achsenbeschriftung nicht las, sah zwei gleich schlimme Netze.

    Auf gemeinsamer Achse ist der Abstand zwischen den Kurven die Aussage.
    Dass der eigene Gipfel der U-Bahn um 16 Uhr liegt, bleibt trotzdem
    ablesbar, weil er als Punkt und Zahl beschriftet ist.
    """
    netze = ["Tram", "U-Bahn"]
    fig = go.Figure()

    # Gemeinsame Skala fuer beide Netze — sonst waere der Vergleich hinfaellig.
    hoechster = werte[spalte].max()

    for von, bis in HVZ_BAENDER:
        fig.add_shape(type="rect", x0=von, x1=bis, y0=0, y1=1,
                      yref="y domain", fillcolor="#ECEFF1", line_width=0,
                      layer="below")

    for i, netz in enumerate(netze):
        t = werte[werte["Netz"] == netz].copy()
        t["x"] = t["stunde"].where(t["stunde"] >= TAGESBEGINN,
                                   t["stunde"] + 24)
        t = t.sort_values("x")
        farbe = FARBE_NETZ[netz]

        fig.add_trace(go.Scatter(
            x=t["x"], y=t[spalte], mode="lines", name=netz,
            line=dict(color=farbe, width=3.5), showlegend=False,
            customdata=t["stunde"],
            hovertemplate=netz + ", %{customdata} Uhr: %{y:.2f} %<extra></extra>",
        ))

        # Der Gipfel ist die Aussage — er bekommt einen Punkt und seine Zahl.
        gipfel = t.loc[t[spalte].idxmax()]
        fig.add_trace(go.Scatter(
            x=[gipfel["x"]], y=[gipfel[spalte]], mode="markers",
            marker=dict(color=farbe, size=16, line=dict(color="white", width=3)),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(
            x=gipfel["x"], y=gipfel[spalte],
            text="<b>" + TEXTE_TAGESGANG_NETZE["gipfel"].format(
                stunde=int(gipfel["stunde"]), wert=_de(gipfel[spalte])) + "</b>",
            showarrow=False, yshift=32, xanchor="center",
            font=dict(size=18, color=farbe))

        # Netzname und Tagesmittel rechts oben, statt einer Legende — so steht
        # die Farbzuordnung direkt neben der Zahl, die sie erklaert. Rechts
        # deshalb, weil dort weder eine Kurve noch eine Gipfelbeschriftung
        # hinreicht; links stiess der Block an das erste Rush-Hour-Band.
        mittel = (t[spalte] * t["n"]).sum() / t["n"].sum()
        fig.add_annotation(
            x=0.995, y=1.0, xref="x domain", yref="y domain",
            yshift=-i * 36, xanchor="right", yanchor="top", showarrow=False,
            text=(f"<b>{netz}</b>   <span style='color:#90A4AE'>"
                  + TEXTE_TAGESGANG_NETZE["mittel"].format(wert=_de(mittel))
                  + "</span>"),
            font=dict(size=21, color=farbe))

    # Beide Baender beschriften, nicht nur das erste. Ein unbeschriftetes
    # zweites Band wird sonst fuer etwas anderes gehalten als das erste.
    for von, bis in HVZ_BAENDER:
        fig.add_annotation(
            x=(von + bis) / 2, y=1.0, xref="x", yref="y domain",
            yanchor="bottom", yshift=8, showarrow=False,
            text=TEXTE_TAGESGANG_NETZE["hvz"],
            font=dict(size=16, color="#90A4AE"))

    # Betriebstag statt Kalendertag: 4 Uhr bis 3 Uhr. Sonst steht der
    # Nachtverkehr als Gipfel am linken Bildrand und konkurriert optisch mit dem
    # Abendgipfel, obwohl er derselbe Betriebsabend ist.
    stellen = list(range(TAGESBEGINN, TAGESBEGINN + 24, 2))
    beschriftung = [f"{s % 24} h" for s in stellen]
    fig.update_xaxes(title=TEXTE_TAGESGANG_NETZE["achse_x"],
                     range=[TAGESBEGINN - 0.5, TAGESBEGINN + 23.5],
                     tickvals=stellen, ticktext=beschriftung,
                     showgrid=False, zeroline=False)
    fig.update_yaxes(title=TEXTE_TAGESGANG_NETZE["achse_y"],
                     range=[0, hoechster * 1.35], gridcolor="#ECEFF1",
                     zeroline=False, ticksuffix=" %")
    fig.update_layout(plot_bgcolor="white", height=560)
    return fig


# ── LSA-Gruppen, gemessen am Puenktlichkeitsfenster ──────────────────────────
#
# Die Zweitfassung zu szene3b_lsa_balken.png. Jene Grafik zeichnet `avg_delay_s`
# — den Mittelwert von delay_s je Haltestelle, ueber die Gruppe gemittelt. Das
# ist genau die Kennzahl, die Szene 4 des Films als irrefuehrend vorfuehrt:
# Verfruehungen tragen negative Werte und ziehen den Mittelwert nach unten.
#
# Der Unterschied ist nicht kosmetisch, er dreht das Ergebnis um. Die sieben
# Halte mit belegt abgeschalteter Beeinflussung stehen im Mittelwert bei 41,1 s
# gegen 27,8 s der aktiven Gruppe — und sehen damit deutlich schlechter aus. Am
# Puenktlichkeitsfenster gemessen liegen sie bei 11,0 % ausserhalb gegen 15,4 %.
# Der Grund steht in der Aufspaltung dieser Grafik: Sie fahren nur halb so oft
# zu frueh (4,9 % gegen 10,2 %), ihr Mittelwert wird also nicht nach unten
# gezogen.
#
# ── Zwei Fassungen, und nur eine davon darf ins Video ────────────────────────
#
# richtungen=False (Vorgabe) zeigt NUR die Verspaetung. Das ist die Fassung fuer
# Szene 6. Der Grund ist dramaturgisch und bindend: Die Verfruehung ist die
# Aufloesung von Szene 8. Wer sie in Szene 6 ins Bild nimmt, verschenkt sie —
# dieselbe Regel gilt fuer die geteilte Richtungsgrafik in Szene 5.
#
# richtungen=True stapelt beide Anteile. Diese Fassung erklaert, warum die
# Mittelwertgrafik ins Gegenteil zeigt, und gehoert in die Anmerkungen und in
# die Fragerunde — nicht in den Film.
#
# ── Die Gruppe "auffaellig" ist zirkulaer ────────────────────────────────────
#
# Sie ist definiert als "aktiv UND avg_delay_s > Mittel + 1,5 sigma der aktiven
# Gruppe" — also als deren oberes Ende. Dass sie hohe Werte hat, ist kein
# Befund, sondern ihre Definition. Sie steht hier nur, weil die bestehende
# Grafik und der Sprechtext sie fuehren; in einer Aussage darf sie nicht
# vorkommen.

TEXTE_LSA_FENSTER = {
    "achse_spaet": "Anteil der Abfahrten mehr als 3½ Minuten zu spät",
    "achse_mittel": "Mittlere Abweichung von der Fahrplanzeit",
    "achse_verspaetung": "Verspätungen ab 0 Sekunden je Abfahrt",
    "achse_ueberzug": "Verspätungen von mehr als 3½ Minuten je Abfahrt",
    "gruppen": {
        "kein_lsa":              "keine Ampel<br>in der Nähe",
        "aktiv":                 "Beeinflussung<br>angenommen",
        "potentiell_ineffektiv": "Ampel,<br>auffällig hohe Verspätung",
        "inaktiv":               "Beeinflussung<br>belegt abgeschaltet",
    },
    "halte": "{n} Halte",
}

# Welche Spalte auf welche Achsenbeschriftung und welche Einheit geht.
#
# Vier Kennzahlen fuer dieselben Gruppen, und sie sagen Verschiedenes — genau
# das ist die Aussage von Szene 6:
#
#     Ø delay_s          Mittelwert, verrechnet Verfruehung gegen Verspaetung
#     Ø Verspätung (s)   Nullpunkt Fahrplanzeit — Verfruehung zaehlt 0
#     zu spät (%)        zaehlt nur, DASS die Grenze ueberschritten wird
#     Ø über Fenster (s) misst in Sekunden AB der Grenze — die 3½ Minuten
#                        sind die Null, verfruehte Abfahrten stehen auf 0
#
# Die beiden mittleren sind die Bruecken. `Ø Verspätung (s)` beantwortet
# "bleibt der Abstand, wenn nur noch Verspaetung zaehlt?", ohne die Einheit zu
# wechseln; `Ø über Fenster (s)` legt zusaetzlich den Vertragsmassstab an. Wer
# den Balkenabstand aus der ersten Kennzahl fuer einen Ampeleffekt haelt, muss
# erklaeren, warum er in den anderen dreien nicht auftaucht.
ACHSEN_LSA = {
    "zu spät (%)":        ("achse_spaet",       " %"),
    "Ø delay_s":          ("achse_mittel",      " s"),
    "Ø Verspätung (s)":   ("achse_verspaetung", " s"),
    "Ø über Fenster (s)": ("achse_ueberzug",    " s"),
}
SPALTE_VERSPAETUNG = "Ø Verspätung (s)"
SPALTE_UEBERZUG = "Ø über Fenster (s)"

# Dieselben Farben wie die Karte in derselben Szene (Notebook 03, Abschnitt 5):
# grau = keine Anlage, gruen = Anlage im Radius, rot = Anlage aus der
# Drucksache. Wer die Balken umfaerbt, muss die Karte mitfaerben.
#
# Gruen neben Rot ist bei Farbfehlsichtigkeit der klassische Problemfall. Hier
# vertretbar, weil jeder Balken seine eigene Beschriftung und seinen Wert traegt
# — die Farbe ist Wiedererkennung zur Karte, nicht die einzige Kodierung.
FARBE_LSA = {
    "kein_lsa":              "#9E9E9E",
    "aktiv":                 "#4CAF50",
    "potentiell_ineffektiv": "#FF9800",
    "inaktiv":               "#F44336",
}

# ── Drei Gruppen, nicht vier ─────────────────────────────────────────────────
#
# `potentiell_ineffektiv` ist NICHT enthalten. Die Gruppe ist definiert als
# "aktiv UND avg_delay_s ueber Mittel + 1,5 sigma der aktiven Gruppe" — also als
# deren oberes Ende. Schneidet man sie heraus, sinkt der Rest der aktiven Gruppe
# kuenstlich ab, und der Abstand zur inaktiven Gruppe waechst:
#
#     zu spaet, aktiv gegen inaktiv   getrennt 1,17x   zusammengefuehrt 1,03x
#
# Die Abspaltung erzeugt damit genau den Effekt, den die Grafik zeigen soll.
# Zusammengefuehrt am 19.08.2026. Die vierte Gruppe bleibt ueber `--getrennt`
# erreichbar, um den Unterschied vorfuehren zu koennen.
REIHENFOLGE_LSA = ["kein_lsa", "aktiv", "inaktiv"]

REIHENFOLGE_LSA_GETRENNT = ["kein_lsa", "aktiv", "potentiell_ineffektiv",
                            "inaktiv"]


def lsa_balken(werte: pd.DataFrame, spalte: str = "zu spät (%)") -> go.Figure:
    """Balken je LSA-Gruppe. `spalte` ist ein Schluessel aus ACHSEN_LSA.

    Die Reihenfolge und damit auch die Zahl der Gruppen kommt aus der Spalte
    `gruppe` von `werte` — das Skript entscheidet, ob zusammengefuehrt wird.
    """
    if spalte not in ACHSEN_LSA:
        raise KeyError(f"unbekannte Spalte {spalte!r}; "
                       f"bekannt sind {sorted(ACHSEN_LSA)}")
    schluessel, einheit = ACHSEN_LSA[spalte]
    gesehen = set(werte["gruppe"])
    ordnung = [g for g in REIHENFOLGE_LSA_GETRENNT if g in gesehen]
    t = werte.set_index("gruppe").reindex(ordnung)

    fig = go.Figure(go.Bar(
        x=[TEXTE_LSA_FENSTER["gruppen"][g] for g in t.index],
        y=t[spalte], width=0.55,
        marker_color=[FARBE_LSA[g] for g in t.index],
        text=[f"<b>{_de(v)}{einheit}</b>" for v in t[spalte]],
        textposition="outside", cliponaxis=False,
        textfont=dict(size=27, color="#37474F"),
        showlegend=False,
        hovertemplate="%{x}: %{text}<extra></extra>",
    ))

    for i, g in enumerate(t.index):
        fig.add_annotation(
            x=i, y=0, yshift=-58, showarrow=False, xanchor="center",
            text=TEXTE_LSA_FENSTER["halte"].format(n=int(t.loc[g, "Halte"])),
            font=dict(size=17, color="#90A4AE"))

    fig.update_layout(
        xaxis=dict(showgrid=False, tickangle=0, zeroline=False),
        yaxis=dict(title=TEXTE_LSA_FENSTER[schluessel],
                   range=[0, float(t[spalte].max()) * 1.30],
                   gridcolor="#ECEFF1", zeroline=False, ticksuffix=einheit),
        plot_bgcolor="white", height=520,
    )
    return fig



# ── Die Obergrenze: was Verspaetungsbekaempfung hoechstens bringen kann ──────
#
# Zu Szene 7 des Films: „Selbst wenn ab morgen keine einzige Tram mehr zu spaet
# kaeme, stiege die Quote auf 89,6 Prozent. Vertraglich geschuldet sind 92,3."
#
# Die Grafik ist der Monatswertegrafik der Senatsverwaltung nachgebaut
# (video/bild/Monatswerte pünktlichkeit.png), aber vollstaendig aus der eigenen
# Erhebung gerechnet — eine Quelle, eine Schwelle, kein Umrechnungsfaktor.
# Gezeichnet werden drei Groeszen:
#
#     ist                so puenktlich war die Tram (Fenster ]-120, +240[)
#     ohne_verspaetung   was uebrig bliebe, wenn ALLE zu spaeten Abfahrten
#                        verschwaenden — also 100 minus Verfruehungsanteil
#     sollwert           Jahressollwert Straszenbahn aus data/bvg/, 92,3 %
#
# Die Flaeche zwischen der zweiten Linie und dem Sollwert ist der Bildinhalt.
# Sie bleibt in jedem Monat offen.
#
# ── DRAMATURGIE: DIE RESTGROESSE WIRD NICHT BENANNT ─────────────────────────
#
# Was uebrig bleibt, sind die verfruehten Abfahrten. Das Wort darf in dieser
# Grafik NICHT vorkommen: Die Verfruehung ist die Aufloesung von Szene 8, und
# Szene 7 laeuft davor. Dieselbe Regel gilt fuer die geteilte Richtungsgrafik
# und fuer lsa_zu_spaet.png. Die Linie heiszt deshalb „wenn keine Fahrt mehr zu
# spaet waere" — sie zeigt eine Luecke, ohne sie zu benennen. Wer die
# Beschriftung auf „Verfruehung" aendert, nimmt die naechste Szene vorweg.
#
# ── WARUM NICHT DIE AMTLICHE REIHE ──────────────────────────────────────────
#
# Eine erste Fassung zeichnete die amtliche Monatsreihe (Jan 25 bis Jun 26) und
# rechnete die zweite Linie ueber das Verhaeltnis der beiden
# Verfruehungsmessungen hoch, Faktor rund 3,4. **Verworfen.** Rechnet man nach,
# wieviel zu spaete Fahrten der geschaetzten Linie noch bleiben, kommt in 12
# von 18 Monaten weniger als 3 % heraus, im Februar und August 2025 ein
# NEGATIVER Wert — die Hypothesenlinie laege dort unter der tatsaechlichen.
# Verspaetungen zu beseitigen kann die Puenktlichkeit aber nicht senken.
#
# Der Grund steht in DATASET.md unter *Known Data Characteristics*: Bei der
# Verfruehung sind sich die beiden Quellen uneinig wie bei keiner anderen
# Kennzahl — amtlich rund 3 % der Fahrten, hier rund 10 %. Das Verhaeltnis ist
# keine Umrechnungskonstante, sondern der Widerspruch selbst.
#
# ── ZWEI EINSCHRAENKUNGEN, DIE IN DEN SPRECHTEXT GEHOEREN ───────────────────
#
# 1. Der Sollwert gilt JE FAHRT, diese Erhebung misst JE ABFAHRT AN EINEM HALT.
#    Beides nebeneinanderzustellen ist genau das, wovor validierung_bvg.py
#    warnt. Belastbar ist es nur, weil dort geprueft wurde, dass die Messung je
#    Halt den amtlichen Wert am besten trifft — der Rest-Abstand betraegt bei
#    der Tram -2,4 bis -3,3 Prozentpunkte, und er geht in die falsche Richtung:
#    Die eigene Messung liegt TIEFER. Rechnet man ihn auf die Hypothesenlinie
#    auf, landet sie bei rund 92,3 % und damit auf dem Sollwert.
#    **Die Luecke ist also nicht groeszer als der bekannte Instrumentenversatz.**
#    Der Satz „ueber die Verspaetung allein ist es nicht erreichbar" bleibt
#    richtig — „knapp verfehlt" waere er nicht.
#
# 2. Die Verfruehungsschwelle ist mit -120 s strenger als die amtliche (-60 s).
#    Sie kann den Verfruehungsanteil deshalb nur unterschaetzen, nie
#    uebertreiben — die Luecke ist in dieser Richtung konservativ.

FARBE_SOLL = "#37474F"      # Sollwertlinie: Struktur, keine Kategorie
FARBE_LUECKE = "#ECEFF1"    # die Flaeche, die auch dann noch fehlt
# Erreichter Sollwert. Keine neue Farbe: derselbe Gruenton wie FARBE_LSA
# ["aktiv"] (#4CAF50), nur als lasierende Flaeche. Wer das Gruen aendert,
# aendert es dort.
FARBE_ERREICHT = "rgba(76, 175, 80, 0.20)"

# Kopfzeile im Aufbau der Senatsgrafik: rote Marke, Titel, Unterzeile.
#
# ZWEI ABWEICHUNGEN VOM AMTLICHEN WORTLAUT, beide bewusst:
#
# 1. „erbrachten ABFAHRTEN" statt „erbrachten Fahrten". Der Monitor zaehlt
#    Fahrten, diese Erhebung Abfahrtsereignisse an einer Haltestelle. Den
#    amtlichen Wortlaut zu uebernehmen hiesze, genau die Verwechslung zu
#    behaupten, vor der scripts/validierung_bvg.py warnt.
# 2. „60 Sekunden vor und 210 Sekunden nach" ist woertlich uebernommen, obwohl
#    auf ]-120 s, +240 s[ gefiltert wird. Das ist die Vertragsregel im
#    Minutenraster — dieselbe Entscheidung wie bei VERTRAGSTEXT und der
#    geteilten Richtungsgrafik. Stuende hier der Rasterwert, hielte der
#    Zuschauer eine der beiden Zahlen fuer falsch.
TEXTE_OHNE_VERSPAETUNG = {
    "titel": "Pünktlichkeit der Tram in meinem Messzeitraum",
    "untertitel": ("Anteil der erbrachten Abfahrten, die innerhalb des Zeitfensters "
                   "von 60 Sekunden vor und 210 Sekunden nach fahrplanmäßiger "
                   "Abfahrtszeit durchgeführt wurden."),
    "ist": "Gemessene Pünktlichkeit",
    "hypothese": "Pünktlichkeit, wenn keine<br>Fahrt verspätet wäre",
    "soll": "Jahressollwert<br>Straßenbahn: {wert} %",
    # Kurz halten: Die Flaeche ist im Bild nur gut zwei Punkte hoch. „⌀" meint
    # das MENGENGEWICHTETE Mittel ueber alle Monate — nicht den besten Monat,
    # der lag bei 2,4. Und „pp", nicht „%": Der Abstand zweier Prozentwerte
    # sind Prozentpunkte.
    "luecke": "⌀ {wert} pp",
}


# Die Schwestergrafik zu Szene 8/9: dieselbe Reihe, aber die andere Richtung
# weggedacht. Hier DARF die Verfruehung benannt werden — sie ist zu diesem
# Zeitpunkt des Films bereits aufgeloest. In der Verspaetungsfassung darf sie es
# nicht, siehe oben.
#
# Beide Grafiken benutzen DIESELBE y-Achse (bis 100 %), damit sie im Schnitt
# uebereinandergelegt werden koennen. Wer eine der beiden skaliert, muss die
# andere mitziehen — sonst sieht die eine Hypothese hoeher aus als die andere,
# obwohl sie es nicht ist.
TEXTE_OHNE_VERFRUEHUNG = {
    "titel": TEXTE_OHNE_VERSPAETUNG["titel"],
    "untertitel": TEXTE_OHNE_VERSPAETUNG["untertitel"],
    "ist": TEXTE_OHNE_VERSPAETUNG["ist"],
    "hypothese": "Pünktlichkeit, wenn keine<br>Fahrt zu früh wäre",
    "soll": TEXTE_OHNE_VERSPAETUNG["soll"],
    "luecke": "Ziel erreicht<br>in {treffer} von {gesamt} Monaten",
}


# Die dritte Fassung — und die einzige, die nichts Unmoegliches annimmt.
#
# „Keine Fahrt mehr zu frueh" ist ein Grenzwert, kein Ziel: Kein Netz der Welt
# faehrt null Verfruehung. Diese Grafik setzt deshalb an ihre Stelle das
# Niveau, das die Berliner U-Bahn im GLEICHEN Zeitraum nachweislich schon
# faehrt — rund ein Prozent gegen rund zehn bei der Tram. Das ist keine
# Modellannahme, sondern eine Messung aus demselben Datensatz.
#
# Was dabei ausdruecklich NICHT mit angenommen wird: dass die Verspaetung
# besser wird. Sie bleibt Monat fuer Monat auf ihrem gemessenen Wert stehen.
# Die Linie zeigt also, was allein die Abfahrtsdisziplin an der Haltestelle
# hergibt — der Teil, fuer den kein Meter Gleis gebaut werden muss.
#
# Die Zahl im Bild ist deshalb belastbarer als die der Verfruehungsfassung,
# und sie liegt zwangslaeufig darunter: genau um die Verfruehung der U-Bahn.
TEXTE_ABFAHRTSDISZIPLIN = {
    "titel": TEXTE_OHNE_VERSPAETUNG["titel"],
    "untertitel": TEXTE_OHNE_VERSPAETUNG["untertitel"],
    "ist": TEXTE_OHNE_VERSPAETUNG["ist"],
    "hypothese": "Pünktlichkeit mit der<br>Abfahrtsdisziplin der U-Bahn",
    "soll": TEXTE_OHNE_VERSPAETUNG["soll"],
    "luecke": "Ziel erreicht<br>in {treffer} von {gesamt} Monaten",
}


def ohne_verspaetung_reihe(es, index: str,
                           monate: list[tuple[str, str, str]],
                           index_vergleich: str | None = None) -> pd.DataFrame:
    """Je Monat: gemessene Puenktlichkeit und die Quote ohne jede Verspaetung.

    `monate` ist eine Liste (Beschriftung, von, bis) mit `bis` exklusiv — die
    Grenzen klammern den Collector-Ausfall aus, statt ihn zu filtern.

    Ist `index_vergleich` gesetzt (die U-Bahn), kommen zwei Spalten dazu:
    `verfrueht_vergleich` — deren Verfruehungsanteil im selben Monat — und
    `wie_vergleich`, die Puenktlichkeit der Tram, wenn ihre Verfruehung auf
    genau dieses Niveau saenke. Das ist die realistische Fassung der
    Hypothese: nicht null Verfruehung, sondern die, die ein anderes Netz im
    selben Zeitraum nachweislich schon faehrt.

    Gerechnet wird ueber `eigene_werte()` aus scripts/validierung_bvg.py, damit
    Grafik, Notebook und die Konsolenausgabe der Validierung dieselbe Abfrage
    benutzen und nicht auseinanderlaufen koennen.

    Liegt hier und nicht im Skript, damit Notebook 05 und
    scripts/grafik_ohne_verspaetung.py dieselbe Rechnung benutzen.
    """
    # scripts/ liegt nicht im Pfad, wenn der Aufruf aus einem Notebook kommt.
    import sys
    from pathlib import Path as _Pfad
    skripte = str(_Pfad(__file__).resolve().parents[2] / "scripts")
    if skripte not in sys.path:
        sys.path.insert(0, skripte)
    from validierung_bvg import eigene_werte

    zeilen = []
    for name, von, bis in monate:
        w = eigene_werte(es, index, von, bis)
        if not w:
            continue
        spaet = w["Verfrühungsvermeidung"] - w["Pünktlichkeit"]
        zeile = {
            "Monat": name,
            "ist": w["Pünktlichkeit"],
            # Keine zu spaete Abfahrt mehr: uebrig bleibt der Verfruehungsanteil.
            "ohne_verspaetung": w["Verfrühungsvermeidung"],
            # Keine zu fruehe Abfahrt mehr: uebrig bleibt der Verspaetungsanteil.
            "ohne_verfruehung": 100 - spaet,
            "zu_frueh": 100 - w["Verfrühungsvermeidung"],
            "zu_spaet": spaet,
            "n": w["_n"],
        }
        if index_vergleich:
            v = eigene_werte(es, index_vergleich, von, bis)
            frueh_v = 100 - v["Verfrühungsvermeidung"]
            zeile["verfrueht_vergleich"] = frueh_v
            # 100 minus Verspaetung minus fremde Verfruehung. Die Verspaetung
            # der Tram bleibt unangetastet — die Annahme lautet ausdruecklich
            # NICHT, dass mit der Disziplin auch die Verspaetung verschwindet.
            zeile["wie_vergleich"] = 100 - spaet - frueh_v
            zeile["n_vergleich"] = v["_n"]
        zeilen.append(zeile)
    return pd.DataFrame(zeilen)


def _bandstuecke(x: list[float], y: list[float], schwelle: float,
                 ueber: bool) -> list[tuple[list[float], list[float]]]:
    """Zerlegt einen Polygonzug in die Stuecke ober- bzw. unterhalb `schwelle`.

    Gibt Listen von (x, y) zurueck, jeweils mit den Schnittpunkten als
    Randpunkten. Damit laesst sich die Flaeche zur Schwelle in zwei Farben
    fuellen, ohne dass an der Kreuzung ein Zipfel in der falschen Farbe stehen
    bleibt — beim Juni geht es um 0,09 Punkte, das waeren wenige Pixel.
    """
    def drin(wert: float) -> bool:
        return wert >= schwelle if ueber else wert <= schwelle

    stuecke, sx, sy = [], [], []
    for i, (xi, yi) in enumerate(zip(x, y)):
        if drin(yi):
            if not sx and i > 0:            # Eintritt: Schnittpunkt davor
                t = (schwelle - y[i - 1]) / (yi - y[i - 1])
                sx.append(x[i - 1] + t * (xi - x[i - 1]))
                sy.append(schwelle)
            sx.append(xi)
            sy.append(yi)
        else:
            if sx:                          # Austritt: Schnittpunkt dahinter
                t = (schwelle - y[i - 1]) / (yi - y[i - 1])
                sx.append(x[i - 1] + t * (xi - x[i - 1]))
                sy.append(schwelle)
                stuecke.append((sx, sy))
                sx, sy = [], []
    if sx:
        stuecke.append((sx, sy))
    return [(a, b) for a, b in stuecke if len(a) > 1]


def _monatsreihe_hypothese(werte: pd.DataFrame, sollwert: float, spalte: str,
                           texte: dict, luecketext: str, text_versatz: float,
                           gruen_ueber_soll: bool = False,
                           versatz_hypothese_px: int = 0,
                           versatz_soll_px: int = 0) -> go.Figure:
    """Gemeinsamer Zeichner beider Hypothesengrafiken.

    `spalte` ist die Hypothesenreihe (`ohne_verspaetung` oder
    `ohne_verfruehung`), `texte` der zugehoerige TEXTE_-Block, `luecketext` die
    schon gefuellte Beschriftung der Flaeche und `text_versatz` ihre Lage in
    Prozentpunkten gegenueber der Bandmitte — die Verfruehungsfassung braucht
    sie ueber dem Band, weil das Band dort nur gut zwei Punkte hoch ist.

    Aufbau wie die Monatswertegrafik der Senatsverwaltung: Kopfzeile mit roter
    Marke, Titel und Unterzeile; links nur die Prozentwerte ohne Achstitel;
    unten die Monate; die Linien rechts am Bildrand beschriftet.
    """
    # Numerische x-Achse statt Kategorien: Nur so lassen sich Schnittpunkte
    # ZWISCHEN zwei Monaten zeichnen. Die Monatsnamen kommen als ticktext.
    x = list(range(len(werte)))
    hypo = list(werte[spalte])
    fig = go.Figure()

    # Die Luecke zuerst, damit die Linien darueber liegen.
    # `mode="lines"` ist Pflicht: Ohne die Angabe setzt Plotly bei wenigen
    # Punkten von sich aus "lines+markers" und tupft blaue Punkte auf den Rand
    # der Flaeche — auf der Sollwertlinie sieht das wie Messwerte aus.
    for stuecke, farbe in ((_bandstuecke(x, hypo, sollwert, ueber=False),
                           FARBE_LUECKE),
                          (_bandstuecke(x, hypo, sollwert, ueber=True),
                           FARBE_ERREICHT if gruen_ueber_soll else FARBE_LUECKE)):
        for sx, sy in stuecke:
            fig.add_trace(go.Scatter(
                x=sx + sx[::-1], y=sy + [sollwert] * len(sx), mode="lines",
                fill="toself", fillcolor=farbe, line_width=0,
                hoverinfo="skip", showlegend=False))

    fig.add_trace(go.Scatter(
        x=x, y=[sollwert] * len(x), mode="lines", showlegend=False,
        line=dict(color=FARBE_SOLL, width=2.5, dash="dot"),
        hovertemplate="Sollwert %{y:.2f} %<extra></extra>"))

    # Gestrichelt: eine Rechnung, keine Messung.
    fig.add_trace(go.Scatter(
        x=x, y=hypo, mode="lines+markers", showlegend=False,
        line=dict(color=FARBE_NETZ["Tram"], width=3.5, dash="dash"),
        marker=dict(color=FARBE_NETZ["Tram"], size=13,
                    line=dict(color="white", width=3)),
        # Neutral formuliert: dieselbe Funktion zeichnet drei verschiedene
        # Hypothesen, „ohne Verspätung" waere bei zweien davon schlicht falsch.
        hovertemplate="gerechnet %{y:.2f} %<extra></extra>"))

    fig.add_trace(go.Scatter(
        x=x, y=list(werte["ist"]), mode="lines+markers", showlegend=False,
        line=dict(color=FARBE_NETZ["Tram"], width=3.5),
        marker=dict(color=FARBE_NETZ["Tram"], size=13,
                    line=dict(color="white", width=3)),
        hovertemplate="gemessen %{y:.2f} %<extra></extra>"))

    # Die Beschriftungen sitzen auf der Hoehe ihrer Linie. Wo Hypothese und
    # Sollwert dicht beieinander enden — bei der Disziplinfassung sind es
    # 0,6 Punkte —, reicht das nicht: zwei zweizeilige Beschriftungen brauchen
    # mehr Platz, als die Linien voneinander haben. Der Versatz in PIXELN, nicht
    # in Prozentpunkten, weil es um Schrifthoehen geht und nicht um Datenwerte.
    letzte = werte.iloc[-1]
    for y, text, farbe, versatz in [
        (letzte["ist"], texte["ist"], FARBE_NETZ["Tram"], 0),
        (letzte[spalte], texte["hypothese"], FARBE_NETZ["Tram"],
         versatz_hypothese_px),
        (sollwert, texte["soll"].format(wert=_de(sollwert)), FARBE_SOLL,
         versatz_soll_px),
    ]:
        fig.add_annotation(x=1.015, y=y, xref="x domain", yref="y",
                           xanchor="left", yanchor="middle", showarrow=False,
                           yshift=versatz,
                           text=text, font=dict(size=17, color=farbe),
                           align="left")

    # Die Zahl steht im BESTEN Monat der Hypothese, nicht im schlechtesten —
    # dort ist die Aussage am schwersten angreifbar.
    bester = werte[spalte].idxmax()
    fig.add_annotation(
        x=int(werte.index.get_loc(bester)),
        y=(sollwert + werte.loc[bester, spalte]) / 2 + text_versatz,
        showarrow=False, xanchor="left", xshift=14, align="left",
        text="<b>" + luecketext + "</b>",
        font=dict(size=17, color=FARBE_SOLL))

    # Kopfzeile im Aufbau der Senatsgrafik: rote Marke, Titel, Unterzeile.
    fig.add_shape(type="rect", xref="paper", yref="paper",
                  x0=-0.052, x1=-0.046, y0=1.055, y1=1.135,
                  fillcolor=FARBE_NETZ["Tram"], line_width=0)
    fig.add_annotation(x=-0.038, y=1.135, xref="paper", yref="paper",
                       xanchor="left", yanchor="top", showarrow=False,
                       text="<b>" + texte["titel"] + "</b>",
                       font=dict(size=25, color="#263238"))
    fig.add_annotation(x=-0.038, y=1.075, xref="paper", yref="paper",
                       xanchor="left", yanchor="top", showarrow=False,
                       text=texte["untertitel"],
                       font=dict(size=15, color="#455A64"))

    tiefste = float(werte["ist"].min())
    fig.update_xaxes(showgrid=False, zeroline=False,
                     tickvals=x, ticktext=list(werte["Monat"]),
                     range=[-0.06, len(werte) - 0.94])
    # Bis 100 %, nicht bis knapp ueber den Sollwert: Der Abstand nach oben ist
    # Teil der Aussage — sonst sieht der Sollwert wie das Maximum aus. Beide
    # Hypothesengrafiken teilen sich diese Achse und sind dadurch im Schnitt
    # uebereinanderlegbar.
    # Kein Achstitel: links stehen nur die Prozentwerte, wie in der Vorlage.
    fig.update_yaxes(range=[tiefste - 1.5, 100], dtick=2,
                     gridcolor="#ECEFF1", zeroline=False, ticksuffix=" %")
    fig.update_layout(plot_bgcolor="white", height=560)
    return fig


def ohne_verspaetung(werte: pd.DataFrame, sollwert: float) -> go.Figure:
    """Szene 7: Puenktlichkeit, wenn keine Abfahrt mehr zu spaet waere.

    Die Luecke bleibt offen — beschriftet wird sie im besten Monat.
    """
    gewicht = werte["n"] / werte["n"].sum()
    mittel = float((werte["ohne_verspaetung"] * gewicht).sum())
    return _monatsreihe_hypothese(
        werte, sollwert, "ohne_verspaetung", TEXTE_OHNE_VERSPAETUNG,
        TEXTE_OHNE_VERSPAETUNG["luecke"].format(wert=_de(sollwert - mittel)),
        text_versatz=0.0)


def ohne_verfruehung(werte: pd.DataFrame, sollwert: float) -> go.Figure:
    """Szene 8/9: Puenktlichkeit, wenn keine Abfahrt mehr zu frueh waere.

    Hier liegt die Hypothesenlinie UEBER dem Sollwert, das Band ist also kein
    Fehlbetrag, sondern ein Ueberschuss — und mit gut zwei Punkten so schmal,
    dass die Beschriftung darueber steht statt darin (`text_versatz`).

    Beschriftet wird, in wievielen Monaten das Ziel erreicht waere. Eine
    einzelne Zahl waere hier irrefuehrend: Drei der vier Monate liegen darueber,
    der Juni mit 92,21 gegen 92,30 % knapp darunter.
    """
    treffer = int((werte["ohne_verfruehung"] >= sollwert).sum())
    return _monatsreihe_hypothese(
        werte, sollwert, "ohne_verfruehung", TEXTE_OHNE_VERFRUEHUNG,
        TEXTE_OHNE_VERFRUEHUNG["luecke"].format(treffer=treffer,
                                                gesamt=len(werte)),
        text_versatz=2.6, gruen_ueber_soll=True)


def abfahrtsdisziplin(werte: pd.DataFrame, sollwert: float,
                      text_versatz: float = 2.0) -> go.Figure:
    """Szene 9b: Puenktlichkeit bei der Abfahrtsdisziplin der U-Bahn.

    Braucht die Spalte `wie_vergleich` — also einen Aufruf von
    `ohne_verspaetung_reihe()` mit `index_vergleich`.

    Dritte und letzte Fassung derselben Grafik, damit sie sich im Schnitt
    uebereinanderlegen lassen: gleiche Achse, gleiche Kopfzeile, gleiche
    Farben. Nur die gestrichelte Linie liegt jeweils anders:

        ohne_verspaetung   Verspaetung = 0   unerreichbar, bleibt unter dem Ziel
        ohne_verfruehung   Verfruehung = 0   unerreichbar, ueber dem Ziel
        abfahrtsdisziplin  Verfruehung = U-Bahn-Niveau, Verspaetung unveraendert

    Die dritte ist die einzige, deren Annahme irgendwo schon eingeloest wird.
    """
    treffer = int((werte["wie_vergleich"] >= sollwert).sum())
    return _monatsreihe_hypothese(
        werte, sollwert, "wie_vergleich", TEXTE_ABFAHRTSDISZIPLIN,
        TEXTE_ABFAHRTSDISZIPLIN["luecke"].format(treffer=treffer,
                                                 gesamt=len(werte)),
        text_versatz=text_versatz, gruen_ueber_soll=True,
        versatz_hypothese_px=52, versatz_soll_px=-26)
