"""Die Vorführung als eine Datei bauen: vorlage.html + Daten eines Messlaufs -> modellassistent-vorfuehrung.html.

    python vorfuehrung/baue.py [nachweis/lauf8]

Die Daten (Antworten des Sprachmodells, Lastenheft, Ausgangsmodell, Kennzahlen) kommen aus dem Messlauf, nie von Hand.
Die fertige Datei braucht keinen Server und lädt nichts nach; sie läuft auch per Doppelklick.
"""
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
LAUF = WURZEL / (sys.argv[1] if len(sys.argv) > 1 else "nachweis/lauf8")
AUS = WURZEL / "vorfuehrung" / "modellassistent-vorfuehrung.html"

VORNE = ["C01", "B02", "D01"]          # drei große Karten auf dem ersten Bildschirm
WEITERE = ["C04", "A02", "D05"]        # kleine Links darunter
ETIKETTEN = {"C01": "Bauteil und Anforderung", "B02": "Anforderung und Funktion", "D01": "zu ungenau: Rückfrage",
             "C04": "Bausteintyp und Bauteil", "A02": "eine Anforderung", "D05": "Widerspruch: Rückfrage"}


def main():
    erg = json.loads((LAUF / "ergebnisse.json").read_text(encoding="utf-8"))
    aufgaben = [json.loads(z) for z in (LAUF / "einzeln.jsonl").read_text(encoding="utf-8").splitlines() if z.strip()]
    ids = VORNE + WEITERE
    felder = ("id", "eingabe", "status", "rueckfragen", "dauer_s", "elemente", "abgerufen", "sysml", "syntax")
    daten = {
        "meta": {k: erg["meta"][k] for k in ("zeit_utc", "sprachmodell", "einbettungsmodell", "prompt_version", "kernel")},
        "kennzahlen": erg["kennzahlen"],
        "vorne": VORNE, "weitere": WEITERE, "etiketten": ETIKETTEN,
        "aufgaben": [{k: a.get(k) for k in felder} for a in aufgaben if a["id"] in ids],
        "modell": (WURZEL / "beispiel" / "ftf.sysml").read_text(encoding="utf-8"),
    }
    fehlend = set(ids) - {a["id"] for a in daten["aufgaben"]}
    if fehlend:
        sys.exit(f"Beispiele fehlen im Lauf: {sorted(fehlend)}")
    vorlage = (WURZEL / "vorfuehrung" / "vorlage.html").read_text(encoding="utf-8")
    json_text = json.dumps(daten, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = vorlage.replace("/*DATEN*/null", json_text)
    if html == vorlage or re.search(r"/\*DATEN\*/", html):
        sys.exit("Platzhalter /*DATEN*/null nicht gefunden")
    AUS.write_text(f"<!-- Erzeugt von vorfuehrung/baue.py aus {LAUF.relative_to(WURZEL)}; nicht von Hand ändern. -->\n" + html,
                   encoding="utf-8")
    print(AUS.relative_to(WURZEL), AUS.stat().st_size, "Bytes,", len(daten["aufgaben"]), "Beispiele")


if __name__ == "__main__":
    main()
