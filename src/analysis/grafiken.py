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
# Die Schwellen sind mit Absicht NICHT symmetrisch. Begruendung siehe
# notebooks/01_eda.ipynb, Abschnitt 3b: Eine Verfruehung kostet den ganzen Takt,
# unabhaengig davon, wie gross sie ist — eine Verspaetung kostet nur ihre eigenen
# Minuten. Zusaetzlich ist delay_s minutenquantisiert (DATASET.md, Known Data
# Characteristic 1); die Klasse "mindestens eine Minute zu spaet" besteht deshalb
# zu grossen Teilen aus Abweichungen unter einer Minute, die auf 60 s gerundet
# wurden. Drei Minuten liegen drei Rasterschritte davon entfernt.
VERFRUEHT_SCHWELLE_S = -60

# Netzfarben wie im ganzen Projekt. Auf Farbfehlsichtigkeit geprueft:
# Abstand 26 (OKLab x100) unter Protanopie, 36 unter Tritanopie — beides weit
# ueber der Grenze von 8. Nicht gegen ein Rot/Gruen-Paar tauschen.
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
    """„1 Minute" / „3 Minuten" — sonst steht im Bild „mindestens 1 Minuten"."""
    minuten = abs(sekunden) // 60
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

    fig = go.Figure()
    for spalte, vorzeichen, richtung in [("zu früh (%)", -1, "zu früh"),
                                         ("zu spät (%)", +1, "zu spät")]:
        fig.add_trace(go.Bar(
            y=reihenfolge, x=vorzeichen * werte[spalte], orientation="h",
            width=0.52, marker_color=farben, showlegend=False,
            text=[f"{_de(v)} %" for v in werte[spalte]],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=15, color="white"),
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
