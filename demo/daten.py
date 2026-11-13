"""Daten der Browser-Vorführung (docs/daten.js) aus einem Messlauf erzeugen, nie von Hand.

    python demo/daten.py [nachweis/lauf8]

Liest die Ergebnisse des Messlaufs (ergebnisse.json, einzeln.jsonl), das Lastenheft und das Ausgangsmodell und schreibt
alles als eine JavaScript-Datei, damit die Vorführung auch per Doppelklick ohne Server läuft. Die Vorführung spielt die
aufgezeichneten Antworten ab; ein Sprachmodell läuft dabei nicht.
"""
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
LAUF = WURZEL / (sys.argv[1] if len(sys.argv) > 1 else "nachweis/lauf8")
AUS = WURZEL / "docs" / "daten.js"

# Reihenfolge der Beispiele oben auf der Seite; alle übrigen Aufgaben stehen in der Liste darunter.
VORNE = ["C01", "B02", "A02", "C04", "D01", "D05"]


def lastenheft():
    absaetze, kapitel = {}, ""
    for zeile in (WURZEL / "wissen" / "lastenheft-ftf.md").read_text(encoding="utf-8").splitlines():
        if zeile.startswith("## "):
            kapitel = zeile[3:].strip()
        m = re.match(r"(LH-\d+\.\d+) (.+)", zeile)
        if m:
            absaetze[m[1]] = {"text": m[2].strip(), "kapitel": kapitel}
    return absaetze


def main():
    erg = json.loads((LAUF / "ergebnisse.json").read_text(encoding="utf-8"))
    aufgaben = [json.loads(z) for z in (LAUF / "einzeln.jsonl").read_text(encoding="utf-8").splitlines() if z.strip()]
    felder = ("id", "eingabe", "status", "rueckfragen", "dauer_s", "elemente", "abgerufen", "sysml", "syntax")
    daten = {
        "meta": erg["meta"],
        "kennzahlen": erg["kennzahlen"],
        "vorne": VORNE,
        "aufgaben": [{k: a.get(k) for k in felder} for a in aufgaben],
        "lastenheft": lastenheft(),
        "modell": (WURZEL / "modell" / "ftf.sysml").read_text(encoding="utf-8"),
        "quelle": str(LAUF.relative_to(WURZEL)),
    }
    fehlend = [v for v in VORNE if v not in {a["id"] for a in aufgaben}]
    if fehlend:
        sys.exit(f"Beispiele fehlen im Lauf: {fehlend}")
    AUS.parent.mkdir(exist_ok=True)
    AUS.write_text("// Erzeugt von demo/daten.py aus " + daten["quelle"] + "; nicht von Hand ändern.\nwindow.DATEN = "
                   + json.dumps(daten, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(AUS.relative_to(WURZEL), len(daten["aufgaben"]), "Aufgaben,", AUS.stat().st_size, "Bytes")


if __name__ == "__main__":
    main()
