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
    "untertitel": ("{monat}. Links meine Erhebung aus der öffentlichen "
                   "Abfahrts-API, rechts der Qualitätsmonitor der "
                   "Senatsverwaltung.<br>Qualitätsmonitor misst je Fahrt, "
                   "ich messe je Halt."),

    # ACHTUNG, zwei verschiedene Dinge:
    #
    # `quellen` sind die SCHLUESSEL in der Spalte `Quelle` des DataFrames. Sie
    # sind der Vertrag mit scripts/grafik_validierung.py — wer sie aendert, muss
    # dort mitaendern, sonst bricht der Zugriff mit einem KeyError ab.
    #
    # `beschriftung` ist der Text, der im BILD unter den Balken steht. Hier
    # gefahrlos aendern; die Zuordnung laeuft ueber den Schluessel links.
    "quellen": ["meine Messung", "amtlich"],
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
    "hinweis": ("Der Qualitätsmonitor misst <b>je Fahrt</b> — "
                "ich messe <b>je Halt</b>."),
    "achse_y": "Anteil der Abfahrten außerhalb des Pünktlichkeitsfensters",
}

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
            marker_color=[FARBE_NETZ[netz],
                          _rgba(FARBE_NETZ[netz], DECKKRAFT_AMTLICH)],
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
        annotations=[
            dict(x=0, y=1.16, xref="paper", yref="paper", xanchor="left",
                 text=f"<b>{TEXTE_ANIMATION['titel']}</b>", showarrow=False,
                 font=dict(size=36, color="#1A3A5C"), visible=False),
            dict(x=0, y=1.05, xref="paper", yref="paper", xanchor="left",
                 text=TEXTE_ANIMATION["hinweis"], showarrow=False,
                 font=dict(size=25, color="#616161"), visible=False),
        ],
        xaxis=dict(categoryorder="array", categoryarray=beschriftet,
                   showgrid=False, tickfont=dict(size=30, color="#37474F")),
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
        margin=dict(t=190, l=130, r=260, b=110),
    )

    # Ein Schritt = ein Klick. `daten` geht an Plotly.restyle, `layout` an
    # Plotly.relayout.
    schritte = [
        {"layout": {"annotations[0].visible": True}},
        {"layout": {"annotations[1].visible": True}},
        {"daten": {"y": [[hoehen["Tram"][0], None],
                         [hoehen["U-Bahn"][0], None]],
                   "text": [[beschriftungen["Tram"][0], ""],
                            [beschriftungen["U-Bahn"][0], ""]]}},
        {"daten": {"y": [hoehen["Tram"], hoehen["U-Bahn"]],
                   "text": [beschriftungen["Tram"],
                            beschriftungen["U-Bahn"]]}},
    ]
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
        fig.update_xaxes(showgrid=False, row=1, col=spalte)

        # Das Verhaeltnis unter jede Quelle. Es ist der eigentliche Beleg: Die
        # beiden Faktoren stehen nebeneinander und sind fast gleich, waehrend die
        # Balkenhoehen es nicht sind.
        for i, q in enumerate(quellen):
            gross, klein = (tabelle.loc[(kennzahl, q), "Tram"],
                            tabelle.loc[(kennzahl, q), "U-Bahn"])
            if klein > gross:
                gross, klein = klein, gross
                wer = "U-Bahn"
            else:
                wer = "Tram"
            fig.add_annotation(
                x=i, y=0, yshift=-46, xref=f"x{spalte if spalte > 1 else ''}",
                yref=f"y{spalte if spalte > 1 else ''}",
                text=f"{wer} <b>{_de(gross / klein)}×</b>", showarrow=False,
                font=dict(size=15, color="#616161"))

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
# Farben: dieselben wie auf den Karten (FARBE_FRUEH tuerkis, FARBE_SPAET orange).
# Das ist Absicht — wer die Karte gesehen hat, liest die Linien ohne Legende.
# Geprueft mit scripts/validate_palette.js des dataviz-Skills: Abstand 19,0
# (OKLab x100) unter Protanopie, 35,2 unter Tritanopie, 30,2 bei normalem Sehen.
# Alle drei weit ueber der Grenze von 8.
#
# ACHTUNG, anderer Filter als anteile_pro_richtung(): Hier wird das
# Analysefenster inklusive Collector-Ausfall angewandt. Bei einer Auswertung nach
# Tagesstunde ist das zwingend — waehrend des Ausfalls wurde unregelmaessig ueber
# den Tag abgetastet, einzelne Stunden waeren dadurch verzerrt. Die Fallzahl
# faellt dadurch von 11,4 auf 9,8 Mio.

FARBE_TAG_FRUEH = "#0097A7"   # identisch mit karten.FARBE_FRUEH
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
    "titel": "Die Tram ist entweder zu früh oder zu spät — je nach Uhrzeit",
    "untertitel": ("Anteil der Tram-Abfahrten außerhalb des Pünktlichkeitsfensters "
                   "nach BVG-Verkehrsvertrag, je Tagesstunde. Die beiden Kurven "
                   "laufen gegeneinander (Spearman −0,48)"),
    "frueh": "zu früh",
    "spaet": "zu spät",
    "achse_x": "Tagesstunde",
    "achse_y": "Anteil der Abfahrten (%)",
    "hinweis_frueh": "die meisten Verfrühungen —<br>und zugleich wenig Verspätung",
    "hinweis_spaet": "die meisten Verspätungen —<br>und die wenigsten Verfrühungen",
}


def tagesgang_anteile(
    es,
    index: str = "tram-departures-v2",
    schwelle_frueh_s: int = VERFRUEHT_SCHWELLE_S,
    schwelle_spaet_s: int = VERSPAETET_SCHWELLE_S,
) -> pd.DataFrame:
    """Anteil zu frueher und zu spaeter Abfahrten je Tagesstunde.

    Rueckgabe: eine Zeile je Stunde mit `stunde`, `n`, `zu früh (%)`,
    `zu spät (%)`.
    """
    from src.analysis.quality import analysefenster_query

    frage = analysefenster_query()
    frage["bool"].setdefault("filter", []).append({"exists": {"field": "delay_s"}})
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
) -> go.Figure:
    """Zwei Linien ueber 24 Stunden, gemeinsame Achse.

    Beide Reihen sind Anteile derselben Grundgesamtheit und teilen sich deshalb
    eine einzige y-Achse. Eine zweite Achse waere hier der klassische Fehler: Sie
    liesse den Massstab frei waehlbar und damit jede gewuenschte Kreuzung der
    beiden Linien erzeugen.
    """
    fig = go.Figure()
    for spalte, farbe, name in (
        ("zu früh (%)", FARBE_TAG_FRUEH, TEXTE_TAGESGANG["frueh"]),
        ("zu spät (%)", FARBE_TAG_SPAET, TEXTE_TAGESGANG["spaet"]),
    ):
        fig.add_trace(go.Scatter(
            x=werte["stunde"], y=werte[spalte], name=name,
            mode="lines+markers", line=dict(color=farbe, width=3),
            marker=dict(size=8, color=farbe,
                        line=dict(width=2, color="white")),
            hovertemplate=f"%{{x}} Uhr — {name} %{{y:.1f}} %<extra></extra>",
        ))

    # Direktbeschriftung am jeweiligen Maximum. Die Position kommt aus den Daten,
    # damit sie nicht stehen bleibt, wenn die Erhebung weiterlaeuft und das
    # Maximum auf eine andere Stunde wandert.
    #
    # Die Versaetze sind gegen die Kurven geprueft, nicht geraten: Beide Marken
    # liegen im leeren Bereich oberhalb der jeweils anderen Linie. ay ist in
    # plotly nach UNTEN positiv — negative Werte heben die Marke an.
    for spalte, farbe, text, ax_px, ay_px in (
        ("zu früh (%)", FARBE_TAG_FRUEH, TEXTE_TAGESGANG["hinweis_frueh"], -95, -45),
        ("zu spät (%)", FARBE_TAG_SPAET, TEXTE_TAGESGANG["hinweis_spaet"], -55, -70),
    ):
        i = werte[spalte].idxmax()
        fig.add_annotation(
            x=werte.loc[i, "stunde"], y=werte.loc[i, spalte],
            text=f"<b>{werte.loc[i, 'stunde']} Uhr</b><br>{text}",
            showarrow=True, arrowhead=0, arrowwidth=2, arrowcolor=farbe,
            ax=ax_px, ay=ay_px, font=dict(size=14, color=farbe),
            align="center", bgcolor="rgba(255,255,255,0.88)", borderpad=4,
        )

    # Kopfraum fuer die beiden Marken. Ohne ihn setzt plotly die Achse knapp
    # oberhalb des Maximums, und die obere Beschriftung wird am Rand abgeschnitten
    # — der Fehler faellt im PNG erst auf, wenn man es ansieht.
    hoechster = max(werte["zu früh (%)"].max(), werte["zu spät (%)"].max())

    fig.update_layout(
        title=dict(text=(f"<b>{TEXTE_TAGESGANG['titel']}</b><br>"
                         f"<span style='font-size:15px;color:#616161'>"
                         f"{TEXTE_TAGESGANG['untertitel']}<br>"
                         f"zu früh ab {_dauer(schwelle_frueh_s)}, zu spät ab "
                         f"{_dauer(schwelle_spaet_s)}</span>"),
                   x=0.01, xanchor="left"),
        xaxis=dict(title=TEXTE_TAGESGANG["achse_x"], dtick=2, showgrid=False,
                   ticksuffix=" h", zeroline=False),
        yaxis=dict(title=TEXTE_TAGESGANG["achse_y"], range=[0, hoechster * 1.22],
                   gridcolor="#ECEFF1", zeroline=False, ticksuffix=" %"),
        # Legende unten links im Bild: Der Bereich zwischen 0 und 8 Uhr liegt
        # unterhalb von 2,5 % und ist bei beiden Reihen frei. Oben rechts waere
        # sie in den Untertitel gelaufen.
        legend=dict(orientation="h", yanchor="bottom", y=0.02,
                    xanchor="left", x=0.01,
                    bgcolor="rgba(255,255,255,0.88)"),
        plot_bgcolor="white", height=430,
    )
    return fig
