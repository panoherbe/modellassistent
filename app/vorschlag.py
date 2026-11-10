"""Vom Satz zum geprüften Modellvorschlag: Abruf → Sprachmodell (JSON nach Schema) → Kennungen → Prüfung → SysML-Text.

Das Sprachmodell antwortet entweder mit Elementen (status „vorschlag“) oder mit Rückfragen (status „rueckfrage“), wenn
die Eingabe für einen prüfbaren Vorschlag nicht reicht. Kennungen vergibt das Programm, nie das Modell.
"""
import re

from . import sysml
from .config import PROMPT_VERSION
from .modell import Modell
from .pruefung import name_normalisieren, pruefen
from .wissen import Quelle

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["vorschlag", "rueckfrage"]},
        "rueckfragen": {"type": "array", "items": {"type": "string"}},
        "elemente": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "ebene": {"type": "string", "enum": ["R", "F", "L", "P"]},
                "name": {"type": "string"},
                "text": {"type": "string"},
                "typ": {"type": "string"},
                "bezuege": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"art": {"type": "string", "enum": ["satisfy", "allocate"]}, "ziel": {"type": "string"}},
                    "required": ["art", "ziel"]}},
                "quellen": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"quelle": {"type": "string"}, "zitat": {"type": "string"}},
                    "required": ["quelle", "zitat"]}},
            },
            "required": ["ebene", "name", "text", "typ", "bezuege", "quellen"]}},
    },
    "required": ["status", "rueckfragen", "elemente"],
}

SYSTEM = """Du bist ein Assistent für modellbasierte Systementwicklung (MBSE) mit SysML v2. Du schlägst Ergänzungen für ein
bestehendes Systemmodell eines autonomen Flurförderfahrzeugs (FTF) vor. Ein Mensch prüft jeden Vorschlag, korrigiert ihn
und gibt ihn frei; du änderst das Modell nie selbst.

RFLP-Ebenen:
- R = Anforderung: was das System leisten muss, prüfbar formuliert, mit Wert und Einheit aus der Eingabe oder der Quelle.
- F = Funktion: eine Tätigkeit des Systems (Name mit Verb, z. B. ladestationAnfahren).
- L = logischer Baustein: eine Teiledefinition (Name ein Substantiv, groß geschrieben, z. B. Ladekontakt).
- P = physisches Teil im Fahrzeug ftf: Name klein geschrieben, Feld "typ" = Name eines L-Bausteins aus dem Modell oder
  aus deinem Vorschlag.

Beziehungen ("bezuege"): "satisfy" verbindet eine Anforderung (R) mit dem Teil (P), das sie erfüllt; "allocate" verbindet
eine Funktion (F) mit dem Teil (P), das sie ausführt. Als "ziel" nimm die Kennung eines vorhandenen Elements (etwa P-004)
oder NEU-1, NEU-2 … für ein Element aus deinem eigenen Vorschlag (Reihenfolge deiner Liste).

Quellen: Belege jedes Element mit mindestens einer Quelle aus dem Kontext (Kennung wie LH-2.3 oder R-004) und einem
wörtlichen Zitat daraus. Erfinde keine Quelle, keinen Wert und keine Kennung.

Rückfrage: Ist die Eingabe zu ungenau für einen prüfbaren Vorschlag (es fehlt ein Wert oder eine Bedingung, es ist
unklar, welches Teil gemeint ist) oder widerspricht sie einer Quelle, dann antworte mit status "rueckfrage", stelle
1 bis 3 kurze Fragen und lass "elemente" leer.

So wählst du die Ebene:
- Fordert die Eingabe eine Eigenschaft oder einen Wert ("soll", "muss", "darf", "höchstens", "mindestens"), schlage eine
  Anforderung (R) vor und verbinde sie per satisfy mit dem vorhandenen Teil (P), das sie erfüllt.
- Verlangt die Eingabe eine Tätigkeit des Fahrzeugs (eine Funktion), schlage eine Funktion (F) vor und ordne sie per
  allocate dem Teil zu, das sie ausführt.
- Verlangt die Eingabe ein neues Bauteil, schlage ein Teil (P) mit Typ vor; nur wenn kein vorhandener Baustein passt,
  zusätzlich einen neuen Baustein (L).
- Nutze vorhandene Teile, wo sie passen; lege nur an, was fehlt.

Regeln:
- Schlage nur NEUE Elemente vor; vorhandene Elemente änderst du nicht und schlägst sie nicht noch einmal vor.
- Für jedes P-Element ist "typ" Pflicht: der Name eines L-Bausteins (vorhanden oder aus deinem Vorschlag).
- Erlaubt sind nur zwei Beziehungen: R satisfy P und F allocate P. Keine anderen, keine auf das Element selbst.
- Jede Anforderung (R) und jede Funktion (F) bekommt genau eine solche Beziehung zu dem Teil (P-...), das sie erfüllt
  oder ausführt: ein vorhandenes Teil aus der Modellübersicht oder ein neues Teil aus deinem Vorschlag (NEU-n).
- Namen: nur Buchstaben und Ziffern, ohne Umlaute und Leerzeichen.
- Schlage nur vor, was die Eingabe verlangt; meist sind es ein bis drei Elemente. Antworte auf Deutsch.

Beispiel 1 (Quelle nur für dieses Beispiel): Quelle X-4 "Das Fahrzeug arbeitet bei Umgebungstemperaturen von 0 bis
40 °C." Eingabe: "Das Fahrzeug soll zwischen 0 und 40 °C arbeiten können." Antwort:
{"status": "vorschlag", "rueckfragen": [], "elemente": [
 {"ebene": "R", "name": "umgebungstemperatur", "text": "Das FTF arbeitet bei Umgebungstemperaturen von 0 bis 40 °C.",
  "typ": "", "bezuege": [{"art": "satisfy", "ziel": "P-001"}],
  "quellen": [{"quelle": "X-4", "zitat": "Umgebungstemperaturen von 0 bis 40 °C"}]}]}

Beispiel 2 (Quelle nur für dieses Beispiel): Quelle X-3 "Die Akkutemperatur wird überwacht; über 60 °C wird der Betrieb
unterbrochen." Eingabe: "Ergänze einen Temperatursensor im Akku." Antwort:
{"status": "vorschlag", "rueckfragen": [], "elemente": [
 {"ebene": "L", "name": "Temperatursensor", "text": "Sensor für die Temperatur des Energiespeichers.", "typ": "",
  "bezuege": [], "quellen": [{"quelle": "X-3", "zitat": "Die Akkutemperatur wird überwacht"}]},
 {"ebene": "P", "name": "akkuTemperatursensor", "text": "Temperatursensor im Akku.", "typ": "Temperatursensor",
  "bezuege": [], "quellen": [{"quelle": "X-3", "zitat": "Die Akkutemperatur wird überwacht"}]},
 {"ebene": "F", "name": "akkutemperaturUeberwachen", "text": "Akkutemperatur überwachen und über 60 °C den Betrieb
  unterbrechen.", "typ": "", "bezuege": [{"art": "allocate", "ziel": "NEU-2"}],
  "quellen": [{"quelle": "X-3", "zitat": "über 60 °C wird der Betrieb unterbrochen"}]}]}"""


KLAERUNG_SCHEMA = {
    "type": "object",
    "properties": {
        "kategorie": {"type": "string", "enum": ["ok", "zielwert_fehlt", "widerspruch", "unklar"]},
        "grund": {"type": "string"},
        "rueckfragen": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["kategorie", "grund", "rueckfragen"],
}

KLAERUNG = """Du prüfst eine Eingabe für einen Modellassistenten (SysML v2, autonomes Flurförderfahrzeug), bevor ein
Modellvorschlag entsteht. Ein Mensch prüft jeden Vorschlag danach ohnehin. Ordne die Eingabe genau einer Kategorie zu:

- "ok": Die Eingabe sagt, was ergänzt werden soll: eine Anforderung mit Wert oder aus einer Quelle, eine Funktion mit
  Zweck, ein Baustein oder Teil mit Zweck. Einbauort, genaue Signalart, Schwellenwerte oder Intervalle darf der Vorschlag
  aus den Quellen übernehmen oder offen lassen. Das ist kein Grund für eine Rückfrage.
- "zielwert_fehlt": Die Eingabe will etwas steigern, senken oder verbessern ("schneller", "mehr", "besser", "erhöhen",
  "verbessern", "sicherer", "leiser"), nennt aber keinen Zielwert.
- "widerspruch": Die Eingabe fordert für eine Größe einen Zahlenwert, der dem Wert für dieselbe Größe in einer Quelle
  widerspricht.
- "unklar": Die Eingabe nennt nur eine Gattung ohne Zweck und ohne Ort, etwa "Ergänze ein Bauteil".

Im Zweifel wähle "ok". Bei jeder anderen Kategorie stelle ein bis drei kurze Rückfragen auf Deutsch, sonst bleibt
"rueckfragen" leer.

Beispiele (Quellen nur für diese Beispiele):
- Quelle X-1 "Die Ladezeit beträgt höchstens 30 Minuten." Eingabe "Die Ladezeit soll 2 Stunden betragen." -> widerspruch
- Eingabe "Das Fahrzeug soll leiser fahren." -> zielwert_fehlt
- Eingabe "Ergänze eine Kamera." -> unklar
- Eingabe "Das Fahrzeug soll im Kühlhaus bei -20 °C arbeiten können." -> ok
- Quelle X-2 "Die Hupe ist aus 5 m Entfernung hörbar." Eingabe "Ergänze eine Hupe als Baustein und baue sie ein." -> ok
- Eingabe "Füge eine Funktion hinzu, mit der das Fahrzeug Türen über Funk öffnet." -> ok
- Eingabe "Ergänze einen Kühlventilator für den Rechner." -> ok"""


def klaeren(eingabe: str, modell: Modell, absaetze: list[tuple[Quelle, float]], llm) -> tuple[dict, float]:
    return llm.json_antwort(KLAERUNG, kontext_text(eingabe, modell, absaetze), KLAERUNG_SCHEMA)


def kontext_text(eingabe: str, modell: Modell, absaetze: list[tuple[Quelle, float]]) -> str:
    lh = "\n".join(f"{q.id}: {q.text}" for q, _ in absaetze)
    return (f"Eingabe: {eingabe}\n\nModell (alle Elemente mit Kennung, Ebene, Name und Beschreibung; dann die "
            f"Beziehungen):\n{modell.uebersicht()}\n\nLastenheft (passende Absätze):\n{lh}")


def erzeugen(eingabe: str, modell: Modell, index, llm, modellquellen: list[Quelle], k: int = 6) -> dict:
    absaetze = index.suchen(eingabe, k=k)
    kontext = {q.id: q for q, _ in absaetze} | {q.id: q for q in modellquellen}
    klaerung, dauer = klaeren(eingabe, modell, absaetze, llm)
    if klaerung.get("kategorie") in ("zielwert_fehlt", "widerspruch", "unklar"):
        fragen = [f for f in klaerung.get("rueckfragen") or [] if f.strip()] or [klaerung.get("grund") or "Bitte präzisieren."]
        roh = {"status": "rueckfrage", "rueckfragen": fragen, "elemente": []}
    else:
        roh, d2 = llm.json_antwort(SYSTEM, kontext_text(eingabe, modell, absaetze), SCHEMA)
        dauer += d2
    v = nachbereiten(roh, modell, kontext)
    v.update({
        "eingabe": eingabe, "dauer_s": round(dauer, 2), "sprachmodell": llm.modell, "prompt_version": PROMPT_VERSION,
        "modell_stand": modell.sha256[:12], "roh": roh, "klaerung": klaerung,
        "abgerufen": [{"id": q.id, "datei": q.datei, "stand": q.stand, "wert": w, "text": q.text} for q, w in absaetze],
    })
    return v


def nachbereiten(roh: dict, modell: Modell, kontext: dict[str, Quelle]) -> dict:
    """Kennungen vergeben, Namen normalisieren, NEU-n auflösen, Beziehungen ausrichten, prüfen, SysML erzeugen."""
    status = roh.get("status") if roh.get("status") in ("vorschlag", "rueckfrage") else "vorschlag"
    elemente, vergeben = [], set()
    for i, e in enumerate(roh.get("elemente") or [], 1):
        ebene = (e.get("ebene") or "?").strip().upper()[:1]
        nid = modell.naechste_id(ebene, vergeben) if ebene in "RFLP" and ebene else f"X-{i:03d}"
        vergeben.add(nid)
        elemente.append({
            "id": nid, "neu": f"NEU-{i}", "ebene": ebene,
            "name": name_normalisieren(e.get("name") or "", ebene), "name_roh": e.get("name") or "",
            "text": (e.get("text") or "").strip(),
            "typ": name_normalisieren(e.get("typ") or "", "L") if ebene == "P" else None,
            "bezuege": [dict(b) for b in e.get("bezuege") or []],
            "quellen": [dict(q) for q in e.get("quellen") or []],
        })
    neu = {e["neu"]: e["id"] for e in elemente}
    neu_name = {e["neu"]: e["name"] for e in elemente if e["ebene"] == "L"}
    for e in elemente:
        if e["ebene"] == "P":
            roh_typ = re.sub(r"^NEU\s*-?\s*", "NEU-", (e["typ"] or "").upper()) if (e["typ"] or "").upper().startswith("NEU") else ""
            if roh_typ in neu_name:
                e["typ"] = neu_name[roh_typ]
        for b in e["bezuege"]:
            ziel = b.get("ziel", "").strip().upper()
            ziel = re.sub(r"^NEU\s*-?\s*", "NEU-", ziel)
            b["ziel"] = neu.get(ziel, ziel)
    _ausrichten(elemente, modell)
    pruefen(elemente, modell, kontext)
    if status == "rueckfrage" and not elemente and not roh.get("rueckfragen"):
        status = "vorschlag"
    ok = [e for e in elemente if e["pruefung"] != "fehler"]
    return {"status": status, "rueckfragen": [f for f in roh.get("rueckfragen") or [] if f.strip()],
            "elemente": elemente, "sysml": sysml.vorschau(ok, modell) if ok else ""}


def _ausrichten(elemente: list[dict], modell: Modell) -> None:
    """Beziehungen gehören zum R- bzw. F-Element („P erfüllt R“ wird „R satisfy P“). Zielt eine Beziehung auf einen
    logischen Baustein (L), den genau ein Teil des Fahrzeugs ausprägt, wird sie auf dieses Teil gelegt (mit Hinweis)."""
    neu = {e["id"]: e for e in elemente}
    for e in elemente:
        if e["ebene"] == "P":
            for b in list(e["bezuege"]):
                if b["ziel"] in neu and neu[b["ziel"]]["ebene"] in "RF":
                    neu[b["ziel"]]["bezuege"].append({"art": b["art"], "ziel": e["id"]})
                    e["bezuege"].remove(b)
                elif b["ziel"] in modell.elemente and modell.elemente[b["ziel"]].ebene in "RF":
                    e.setdefault("bezuege_von", []).append({"art": b["art"], "quelle": b["ziel"]})
                    e["bezuege"].remove(b)
    for e in elemente:
        if e["ebene"] not in "RF":
            continue
        for b in e["bezuege"]:
            ziel = modell.elemente.get(b["ziel"])
            ziel_name = ziel.name if ziel and ziel.ebene == "L" else (
                neu[b["ziel"]]["name"] if b["ziel"] in neu and neu[b["ziel"]]["ebene"] == "L" else None)
            if ziel_name:
                teile = [(p.id, p.name) for p in modell.elemente.values() if p.ebene == "P" and p.typ == ziel_name] + \
                        [(p["id"], p["name"]) for p in elemente if p["ebene"] == "P" and p.get("typ") == ziel_name]
                if len(teile) == 1:
                    e.setdefault("hinweise", []).append(f"Ziel {b['ziel']} ({ziel_name}) auf das Teil {teile[0][0]} "
                                                        f"({teile[0][1]}) gelegt")
                    b["ziel"] = teile[0][0]
    _bereinigen(elemente, modell)


def _bereinigen(elemente: list[dict], modell: Modell) -> None:
    """Unzulässige Beziehungen (falsche Art, auf sich selbst, unbekanntes Ziel) nimmt das Programm heraus und sagt es;
    fehlt einem Teil (P) der Typ und schlägt der Vorschlag genau einen neuen Baustein (L) vor, wird dieser eingesetzt."""
    ebene = {e["id"]: e["ebene"] for e in elemente} | {i: x.ebene for i, x in modell.elemente.items()}
    zulaessig = {("satisfy", "R", "P"), ("allocate", "F", "P")}
    for e in elemente:
        for b in list(e["bezuege"]):
            if (b.get("art"), e["ebene"], ebene.get(b["ziel"])) not in zulaessig or b["ziel"] == e["id"]:
                e["bezuege"].remove(b)
                e.setdefault("hinweise", []).append(
                    f"Beziehung {b.get('art')} → {b['ziel']} nicht übernommen (zulässig: R satisfy P, F allocate P)")
        if e["ebene"] == "P" and not e.get("typ"):
            neue_l = [x for x in elemente if x["ebene"] == "L"]
            if len(neue_l) == 1:
                e["typ"] = neue_l[0]["name"]
                e.setdefault("hinweise", []).append(f"Typ fehlte; neuer Baustein {neue_l[0]['name']} eingesetzt")

