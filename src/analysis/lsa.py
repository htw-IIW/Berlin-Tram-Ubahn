# src/analysis/lsa.py
# Ordnet Haltestellen die nächstgelegene Lichtsignalanlage zu und führt deren
# ÖPNV-Beeinflussungsstatus mit.
#
# ── Was "Beeinflussung" hier heißt ───────────────────────────────────────────
#
# Der Senat schreibt in der Drucksache 19/19804 ausdrücklich
# "ÖPNV-Beeinflussung" und nicht "Vorrang": Ein absoluter Vorrang sei im
# Stadtverkehr wegen der Zielkonflikte mit dem übrigen Verkehr meist nicht
# möglich. Diese Auswertung übernimmt den Begriff.
#
# ── Woher der Status kommt, und was er nicht sagt ────────────────────────────
#
# Der WFS-Datensatz der Senatsverwaltung enthält die Koordinaten und
# Bezeichnungen aller 2.305 Berliner LSA — aber **keine** Angabe darüber, ob an
# einer Anlage die ÖPNV-Beeinflussung tatsächlich in Betrieb ist. Der Status im
# Index entsteht deshalb aus zwei verschiedenen Quellen:
#
#   aktiv            LSA liegt im 150-m-Radius einer Tram-Haltestelle und steht
#                    NICHT in der parlamentarischen Ausnahmeliste.
#                    Das ist eine Annahme, kein Beleg. 307 Anlagen.
#   inaktiv          Beeinflussung vorhanden, aber nicht in Betrieb — belegt
#                    durch Drucksache 19/19804 vom 07.08.2024. 6 Anlagen.
#   nicht_vorhanden  keine Beeinflussung eingebaut — ebenfalls aus der
#                    Drucksache. 1 Anlage.
#   kein_tram        LSA ohne Tramstrecke im Umkreis. 1.987 Anlagen.
#   unklar           siehe Korrektur 1 unten.
#
# Die Drucksache deckt nur die Linien M4 und M5 ab. Für alle übrigen Anlagen
# gibt es keine Primärquelle — "aktiv" heißt dort ausschließlich "nicht als
# defekt bekannt". Wer daraus einen Effekt schätzt, schätzt den Effekt einer
# Klassifikation, deren positive Kategorie ungeprüft ist.
#
# ── Zwei Korrekturen gegen die Primärquelle ──────────────────────────────────
#
# Sie werden hier in der Analyse vorgenommen und nicht im Index, damit die
# Abweichung sichtbar und die Korrektur umkehrbar bleibt.
#
#   1. ALEXANDERSTRASSE — sieben Anlagen zu viel. Der Index führt sieben
#      Anlagen als "nicht_vorhanden"; die Drucksache nennt genau eine
#      ("Alexanderstraße / Gleisquerung"). Der Seed hat offenbar auf den
#      Straßennamen gemustert — ausgerechnet die Anlage, die dem Namen wörtlich
#      entspricht ("Alexanderpl. / Gleisquerung"), steht als aktiv im Index.
#      Die sieben werden auf "unklar" gesetzt und aus Gruppenvergleichen
#      genommen. Nicht weil belegt wäre, dass sie eine Beeinflussung haben,
#      sondern weil die Quelle das Gegenteil nicht belegt.
#
#   2. ZWEI ANLAGEN FEHLEN. Antonplatz und Berliner Allee/Buschallee führt die
#      Drucksache als inaktiv, im Index kommen sie nicht vor. Sie werden mit
#      den Koordinaten der gleichnamigen Tram-Haltestelle ergänzt; die Anlage
#      liegt an der Kreuzung, die Haltestelle unmittelbar daneben und damit
#      sicher innerhalb des Radius.
#
# Die Zuordnungslogik entspricht der von notebooks/03_lsa_analyse.ipynb
# (Zellen `sec1-load-lsa`, `d0436d43`, `sec2-join`); sie steht hier, damit
# Auswertungen außerhalb des Notebooks nicht ihre eigene Fassung bauen.

import numpy as np
import pandas as pd
from elasticsearch.helpers import scan

INDEX_LSA = "lsa-standorte"

# Eine Anlage gilt als "zu dieser Haltestelle gehörend", wenn sie innerhalb
# dieses Radius liegt. Derselbe Wert wie in src/collector/enrich_lsa_tram.py,
# mit dem der Status im Index vergeben wurde — ein anderer Radius hier würde
# Haltestellen Anlagen zuordnen, die bei der Statusvergabe nie gesehen wurden.
# Notebook 03 prüft 100/150/200/250 m; der Befund hängt nicht am Radius.
RADIUS_METERS = 150

# ── Zwei Dimensionen, nicht eine Skala ───────────────────────────────────────
#
# `oepnv_status` sieht aus wie eine Rangfolge von "aktiv" bis "kein_lsa", mischt
# aber zwei Fragen, die verschieden gut beantwortbar sind:
#
#   1. Liegt überhaupt eine Anlage an dieser Haltestelle?
#      Reine Geometrie, für jede Haltestelle gemessen.  ->  lsa_vorhanden
#
#   2. Ist die ÖPNV-Beeinflussung dort in Betrieb?
#      Nur für die 11 Anlagen der Drucksache beantwortet, und die deckt
#      ausschließlich M4 und M5 ab.                      ->  beeinflussung_belegt
#
# `aktiv` beantwortet Frage 1 mit ja und über Frage 2 gar nichts — es heißt
# wörtlich "im Radius einer Haltestelle und nicht auf der Drucksachenliste"
# (siehe src/collector/enrich_lsa_tram.py). Eine Spalte
# `hat_oepnv_beeinflussung = True` für diese Anlagen wäre eine Behauptung, für
# die es keine Quelle gibt; deshalb gibt es sie hier nicht.
#
# Dieselbe Trennung liegt der Karte in Notebook 03 zugrunde: grau = keine
# Anlage, grün = Anlage im Radius, rot = Anlage aus der Drucksache.

# Frage 2, so weit die Quellenlage reicht.
BELEGLAGE = {
    "inaktiv":         "inaktiv_belegt",          # vorhanden, nicht in Betrieb
    "nicht_vorhanden": "nicht_vorhanden_belegt",  # keine eingebaut
    "unklar":          "unklar",                  # Zuordnung nicht eindeutig
    "aktiv":           "nicht_belegt",            # über diese Anlage sagt niemand etwas
    "kein_tram":       "nicht_belegt",
    "kein_lsa":        "nicht_belegt",
}

# Die Linien, die die Drucksache 19/19804 geprüft hat. Für alle anderen Linien
# gibt es keine Aussage — weder eine positive noch eine negative. Ein Vergleich
# der belegt-inaktiven Anlagen gegen das gesamte Netz vermengt deshalb den
# Effekt der Beeinflussung mit der Frage, welche Linien überhaupt untersucht
# wurden. Die saubere Vergleichsgruppe liegt innerhalb dieser Linien.
DRUCKSACHE_LINIEN = ("M4", "M5")

# Aus Drucksache 19/19804 ergänzte Anlagen (Korrektur 2).
NACHTRAG_DRUCKSACHE = [
    {"lsa_id": "drs-19804-antonplatz", "bezeichnung": "Antonplatz",
     "standort": None, "lat": 52.54829, "lon": 13.45086,
     "oepnv_status": "inaktiv",
     "oepnv_bemerkung": "neue Software nach Knotenumbau in Projektierung",
     "tram_linien": []},
    {"lsa_id": "drs-19804-buschallee", "bezeichnung": "Berliner Allee / Buschallee",
     "standort": None, "lat": 52.55367, "lon": 13.46935,
     "oepnv_status": "inaktiv",
     "oepnv_bemerkung": "Bauzustand Berliner Wasserbetriebe",
     "tram_linien": []},
]


def lade_lsa(es, korrigieren: bool = True) -> pd.DataFrame:
    """
    Alle LSA-Standorte, standardmäßig mit den Korrekturen gegen die Drucksache.

    `korrigieren=False` liefert den Rohstand des Index — nützlich, um zu zeigen,
    was die Korrekturen bewirken.
    """
    zeilen = []
    for hit in scan(es, index=INDEX_LSA, query={"query": {"match_all": {}}},
                    size=5000,
                    _source=["lsa_id", "standort", "bezeichnung", "location",
                             "oepnv_status", "oepnv_bemerkung", "tram_linien"]):
        s = hit["_source"]
        ort = s.get("location") or {}
        zeilen.append({
            "lsa_id":          s.get("lsa_id"),
            "bezeichnung":     s.get("bezeichnung"),
            "standort":        s.get("standort"),
            "lat":             ort.get("lat"),
            "lon":             ort.get("lon"),
            "oepnv_status":    s.get("oepnv_status"),
            "oepnv_bemerkung": s.get("oepnv_bemerkung"),
            "tram_linien":     s.get("tram_linien") or [],
        })

    df = pd.DataFrame(zeilen)
    if not korrigieren:
        return df

    # Korrektur 1: Alexanderstraße
    alex = (df["bezeichnung"].fillna("").str.contains("Alexanderstr", case=False)
            & (df["oepnv_status"] == "nicht_vorhanden"))
    df.loc[alex, "oepnv_status"] = "unklar"

    # Korrektur 2: fehlende Anlagen nachtragen
    df = pd.concat([df, pd.DataFrame(NACHTRAG_DRUCKSACHE)], ignore_index=True)
    return df


def _distanzen_m(df_lsa: pd.DataFrame, lat: float, lon: float) -> np.ndarray:
    """Ebene Näherung — auf Berliner Breite und 150 m Radius genau genug."""
    d_lat = (df_lsa["lat"].to_numpy() - lat) * 111_320
    d_lon = (df_lsa["lon"].to_numpy() - lon) * 111_320 * np.cos(np.radians(lat))
    return np.sqrt(d_lat**2 + d_lon**2)


def naechste_lsa(df_lsa: pd.DataFrame, lat: float, lon: float,
                 radius_m: float = RADIUS_METERS) -> dict:
    """
    Die nächstgelegene Anlage im Radius — oder der Merker, dass es keine gibt.

    Gesucht wird die nächste Anlage, nicht die "schlechteste" im Umkreis. Eine
    Haltestelle mit zwei Anlagen im Radius bekommt damit den Status der
    näheren; `lsa_im_radius` hält fest, dass es mehrere waren.
    """
    distanz = _distanzen_m(df_lsa, lat, lon)
    im_radius = distanz <= radius_m
    if not im_radius.any():
        return {"lsa_status": "kein_lsa", "lsa_distanz_m": np.nan,
                "lsa_id": None, "lsa_bezeichnung": None,
                "lsa_bemerkung": None, "lsa_im_radius": 0}

    treffer = df_lsa.iloc[int(np.where(im_radius, distanz, np.inf).argmin())]
    return {
        "lsa_status":      treffer["oepnv_status"],
        "lsa_distanz_m":   float(distanz[im_radius].min()),
        "lsa_id":          treffer["lsa_id"],
        "lsa_bezeichnung": treffer["bezeichnung"],
        "lsa_bemerkung":   treffer["oepnv_bemerkung"],
        "lsa_im_radius":   int(im_radius.sum()),
    }


def lsa_je_haltestelle(df_stops: pd.DataFrame, df_lsa: pd.DataFrame,
                       radius_m: float = RADIUS_METERS) -> pd.DataFrame:
    """
    Ergänzt einen Haltestellen-DataFrame (`lat`, `lon`) um die LSA-Spalten.

    Dazu die beiden getrennten Dimensionen: `lsa_vorhanden` (Geometrie,
    gemessen) und `beeinflussung_belegt` (Quellenlage, siehe BELEGLAGE).
    """
    treffer = pd.DataFrame(
        [naechste_lsa(df_lsa, r.lat, r.lon, radius_m)
         for r in df_stops.itertuples()],
        index=df_stops.index,
    )
    ergebnis = df_stops.join(treffer)
    ergebnis["lsa_vorhanden"] = (
        ergebnis["lsa_status"].ne("kein_lsa").astype("boolean"))
    ergebnis["beeinflussung_belegt"] = ergebnis["lsa_status"].map(BELEGLAGE)
    return ergebnis


def haltestellen_koordinaten(es, index: str, max_haltestellen: int = 2000
                             ) -> pd.DataFrame:
    """
    Eine Zeile je Haltestelle: Koordinaten, mittlere Verspätung, Zahl der
    Abfahrten — aus einer einzigen Aggregation über den Abfahrtsindex.

    Die Koordinaten stammen aus `top_hits`, weil `stop_location` je Haltestelle
    konstant ist; ein Dokument genügt.
    """
    antwort = es.search(
        index=index, size=0,
        aggs={"stops": {
            "terms": {"field": "stop_name", "size": max_haltestellen},
            "aggs": {
                "avg_delay": {"avg": {"field": "delay_s"}},
                "n_delay":   {"value_count": {"field": "delay_s"}},
                "linien":    {"terms": {"field": "line_name", "size": 30}},
                "ort":       {"top_hits": {"size": 1,
                                           "_source": ["stop_location", "stop_id"]}},
            },
        }},
    )

    zeilen = []
    for eimer in antwort["aggregations"]["stops"]["buckets"]:
        treffer = eimer["ort"]["hits"]["hits"]
        if not treffer:
            continue
        quelle = treffer[0]["_source"]
        ort = quelle.get("stop_location") or {}
        if ort.get("lat") is None:
            continue
        linien = sorted(b["key"] for b in eimer["linien"]["buckets"])
        zeilen.append({
            "stop_name":    eimer["key"],
            "stop_id":      quelle.get("stop_id"),
            "lat":          ort["lat"],
            "lon":          ort["lon"],
            "linien":       ";".join(linien),
            # Nur auf diesen Linien hat die Drucksache überhaupt nachgesehen.
            "auf_drucksachen_linie": any(l in DRUCKSACHE_LINIEN for l in linien),
            "n_abfahrten":  eimer["doc_count"],
            "n_mit_delay":  eimer["n_delay"]["value"],
            "avg_delay_s":  eimer["avg_delay"]["value"],
        })

    return pd.DataFrame(zeilen).dropna(subset=["avg_delay_s"])
