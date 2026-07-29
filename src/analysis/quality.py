# src/analysis/quality.py
# Zentrale Datenqualitäts-Regeln für alle Auswertungs-Notebooks.
#
# Hintergrund: Die Rohdaten enthalten drei systematische Eigenheiten, die vor
# jeder inhaltlichen Auswertung berücksichtigt werden müssen. Sie sind hier
# einmal dokumentiert und als Filter verfügbar, damit die Notebooks nicht
# jeweils eigene (und voneinander abweichende) Schwellen definieren.
#
#   1. delay_s ist minutenquantisiert (siehe DELAY_QUANTISIERUNG_S)
#   2. Der Collector fiel vom 27.06. bis 07.07.2026 weitgehend aus
#   3. Einige "Haltestellen" sind Betriebspunkte, keine Fahrgasthalte
#
# Die Herleitung dieser Werte steht in Notebook 01, Abschnitt "Plausibilität".

import re

# ── 1. Analysefenster ────────────────────────────────────────────────────────
#
# Erhebungsbeginn ist der 24.04.2026, die ersten drei Tage sind aber nur
# teilbefüllt (9.888 / 24.111 / 18.905 Dokumente gegenüber ~140.000 im
# Regelbetrieb) — der Collector lief in dieser Zeit im Testbetrieb.
# Analysebeginn ist deshalb der erste vollständige Tag.

ANALYSE_START = "2026-04-27"
ANALYSE_ENDE  = "2026-07-29"   # laufende Erhebung; Stand der Auswertung

# Collector-Ausfall: In diesem Zeitraum wurden pro Tag zwischen 943 und 12.000
# Dokumente erfasst statt der üblichen ~140.000. Die verbliebenen Daten sind
# nicht repräsentativ (unregelmäßige Abtastung über den Tag) und werden für
# ratenbasierte Auswertungen ausgeschlossen.

COLLECTOR_AUSFALL_START = "2026-06-27"
COLLECTOR_AUSFALL_ENDE  = "2026-07-08"

# Für Ausfallquoten (cancelled) gilt eine zusätzliche Einschränkung, die NUR
# die U-Bahn betrifft. Nach dem Neustart des Collectors am 08.07. fällt die
# U-Bahn-Ausfallquote von 1,160 % auf 0,062 % — Faktor 19 —, während alles
# andere unverändert bleibt:
#
#                        U-Bahn vor      U-Bahn nach
#   Dokumente/Tag        ~76.000         ~76.000
#   Haltestellen         169             169
#   delay-Abdeckung      83,9 %          98,3 %
#   p90 / p95            82 / 134 s      85 / 138 s
#   Anteil >= 180 s      3,97 %          4,16 %
#   cancelled            1,160 %         0,062 %      <-- einziger Bruch
#
# Zwei Belege dafür, dass es sich um ein Erfassungs- und nicht um ein
# Verkehrsereignis handelt:
#
#   - Die Tram macht den Bruch nicht mit (0,521 % -> 0,520 % über denselben
#     Neustart). Der Collector-Neustart hat cancelled also nicht generisch
#     beschädigt, sondern nur für die U-Bahn.
#   - Sechs Tage nach dem Neustart weisen exakt 0 Ausfälle aus (11.07., 17.07.,
#     23.07., 26.07., 28.07., 29.07.). Bei ~76.000 Abfahrten pro Tag ist eine
#     Ausfallquote von exakt null nicht plausibel.
#
# Vermuteter Mechanismus: Die API liefert ausgefallene Fahrten seit dem
# Neustart nicht mehr aus, statt sie zu markieren — das erklärt den
# gleichzeitigen Anstieg der delay-Abdeckung und das Verschwinden der Ausfälle.

AUSFALL_VERGLEICHSFENSTER = (ANALYSE_START, "2026-06-27")

# Die delay-Abdeckung springt über den Neustart in BEIDEN Netzen deutlich
# (Tram 81,0 % -> 95,5 %, U-Bahn 83,9 % -> 98,3 %). Fahrten ohne Echtzeitdaten
# sind vermutlich nicht zufällig, sondern überdurchschnittlich oft gestört.
# Deshalb gilt: Querschnittsvergleiche über das gesamte Fenster sind zulässig,
# ZEITTRENDS der Verspätung über den 07.07. hinweg sind es nicht — ein Anstieg
# könnte allein aus der veränderten Erfassung stammen.

TRENDBRUCH = "2026-07-08"


# ── 2. Eigenschaften von delay_s ─────────────────────────────────────────────
#
# Sämtliche 9,8 Mio. delay_s-Werte im Tram-Index sind exakte Vielfache von 60.
# Die BVG-API liefert Verspätungen ausschließlich in ganzen Minuten. Das hat
# zwei Konsequenzen:
#
#   - Mediane einzelner Abfahrten sind faktisch nur 0, 60, 120 … Sekunden.
#     Ein "Median von 28,3 s" kann nur als Mittel über Haltestellen entstehen
#     und darf nicht als Sekundengenauigkeit interpretiert werden.
#   - Rangtests auf Einzelabfahrten sind stark bindungsbehaftet (ties).
#     Belastbarer sind Anteilswerte, siehe VERSPAETET_SCHWELLE_S.

DELAY_QUANTISIERUNG_S = 60

# Kappungsgrenze für Verteilungsdarstellungen. Werte jenseits ±600 s sind
# überwiegend Artefakte (Fahrplanwechsel, zurückgezogene Echtzeitprognosen);
# das Minimum liegt bei -4020 s, das Maximum bei +3540 s.
DELAY_CLIP_S = 600

# Schwelle für "spürbar verspätet". 180 s entspricht drei Quantisierungs-
# stufen und liegt oberhalb des 75.-Perzentils beider Netze — damit ist der
# Anteil darüber eine robuste, quantisierungsfeste Kennzahl.
VERSPAETET_SCHWELLE_S = 180


# ── 3. Betriebliche Haltestellen ─────────────────────────────────────────────
#
# Betriebshöfe, Ausstiegs- und Endstellen sind keine regulären Fahrgasthalte.
# Fahrzeuge stehen dort planmäßig länger, wodurch systematisch hohe
# "Verspätungen" entstehen, die kein Fahrgast erlebt.
#
# Achtung: Eckige Klammern allein sind KEIN Ausschlusskriterium. Die meisten
# geklammerten Namen unterscheiden lediglich Bahnsteige derselben Haltestelle
# ("U Alexanderplatz (Berlin) [Tram]", "Roederplatz (Berlin) [Weißenseer Weg]")
# und sind reguläre Halte.

_BETRIEBLICH_PATTERN = re.compile(
    r"\[\s*Ausstieg\s*\]"      # z. B. "Altes Wasserwerk (Berlin) [Ausstieg]"
    r"|\[\s*Endstelle\s*\]"    # z. B. "Hirtestr. (Berlin) [Endstelle]"
    r"|^\s*Betriebshof\b",     # z. B. "Betriebshof Marzahn (Berlin)"
    re.IGNORECASE,
)


def ist_betriebliche_haltestelle(stop_name: str) -> bool:
    """True, wenn der Haltestellenname einen Betriebspunkt bezeichnet."""
    if not stop_name:
        return False
    return bool(_BETRIEBLICH_PATTERN.search(stop_name))


# Zur Dokumentation im Notebook: die konkret betroffenen Namen im aktuellen
# Datenbestand. Die Prüfung erfolgt über ist_betriebliche_haltestelle(),
# nicht über diese Liste — sie dient nur der Nachvollziehbarkeit.
BETRIEBLICHE_HALTESTELLEN = (
    "Betriebshof Marzahn (Berlin)",
    "Betriebshof Indira-Gandhi-Str. (Berlin)",
    "Betriebshof Lichtenberg (Berlin)",
    "Betriebshof Köpenick (Berlin)",
    "Betriebshof Weißensee (Berlin)",
    "Hirtestr. (Berlin) [Endstelle]",
    "Haeckelstr. (Berlin) [Ausstieg]",
    "Altes Wasserwerk (Berlin) [Ausstieg]",
)


# ── Query-Bausteine für Elasticsearch ────────────────────────────────────────

def analysefenster_query(
    feld: str = "planned_when",
    ausfall_ausschliessen: bool = True,
) -> dict:
    """
    Elasticsearch-Filter für das reguläre Analysefenster.

    ausfall_ausschliessen=True klammert zusätzlich den Collector-Ausfall aus.
    Das ist für alle Auswertungen nötig, die auf gleichmäßiger Abtastung
    beruhen (Tagesgänge, Raten, Fahrtenrekonstruktion). Für reine
    Verteilungsbetrachtungen einzelner Abfahrten ist es nicht zwingend.
    """
    muss = [{"range": {feld: {"gte": ANALYSE_START, "lte": ANALYSE_ENDE}}}]
    darf_nicht = []
    if ausfall_ausschliessen:
        darf_nicht.append({
            "range": {feld: {
                "gte": COLLECTOR_AUSFALL_START,
                "lt":  COLLECTOR_AUSFALL_ENDE,
            }}
        })
    return {"bool": {"must": muss, "must_not": darf_nicht}}


def sauberes_ausfallfenster_query(feld: str = "planned_when") -> dict:
    """
    Filter für Ausfallquoten-Vergleiche (cancelled).

    Beschränkt auf den Zeitraum vor dem Collector-Ausfall, weil die
    cancelled-Erfassung danach nachweislich unvollständig ist.
    """
    start, ende = AUSFALL_VERGLEICHSFENSTER
    return {"range": {feld: {"gte": start, "lt": ende}}}


def beschreibe_filter() -> str:
    """Menschenlesbare Zusammenfassung der aktiven Regeln — für Notebook-Ausgaben."""
    start, ende = AUSFALL_VERGLEICHSFENSTER
    return (
        f"Analysefenster:        {ANALYSE_START} bis {ANALYSE_ENDE}\n"
        f"Ausgeschlossen:        {COLLECTOR_AUSFALL_START} bis {COLLECTOR_AUSFALL_ENDE} "
        f"(Collector-Ausfall)\n"
        f"Ausfallquoten nur:     {start} bis {ende} "
        f"(danach cancelled-Erfassung unvollständig)\n"
        f"delay_s-Auflösung:     {DELAY_QUANTISIERUNG_S} s (minutenquantisiert)\n"
        f"Kappung Verteilungen:  ±{DELAY_CLIP_S} s\n"
        f"Verspätet ab:          {VERSPAETET_SCHWELLE_S} s\n"
        f"Ausgeschl. Haltestellen: Betriebshöfe, [Ausstieg], [Endstelle]"
    )
