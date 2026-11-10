"""Messprotokoll aus allen Läufen in nachweis/ schreiben: nachweis/PROTOKOLL.md (alle Läufe, auch die schlechteren).

    python -m eval.protokoll
"""
import json
import re
from pathlib import Path

N = Path(__file__).resolve().parent.parent / "nachweis"
AENDERUNG = {
    "lauf1": "ein Schritt: Vorschlag direkt (Prompt vorschlag-v1)",
    "lauf2": "Klärung davor, ausreichend ja/nein (klaerung-v1); Prompt vorschlag-v2 mit einem Beispiel",
    "lauf3": "Klärung mit vier Kategorien und „im Zweifel ok“ (klaerung-v2); unzulässige Beziehungen entfernt statt gesperrt",
    "lauf4": "Regeln zur Wahl der RFLP-Ebene, zweites Beispiel (vorschlag-v3), Beschreibung der Teile in der Modellübersicht",
    "lauf5": "jede Anforderung und Funktion braucht eine Beziehung zu einem Teil (vorschlag-v4); Typ „NEU-n“ aufgelöst",
    "lauf6": "Beziehung auf einen neuen Baustein (L) wird auf das Teil gelegt, das ihn ausprägt (zuordnung-v2)",
}


def main():
    z = ["# Messprotokoll Modellassistent", "",
         "Aufgaben: `eval/aufgaben.yaml` (24, selbst geschrieben, synthetisch: 17 präzise, 7 ungenau oder widersprüchlich).",
         "Je Lauf alle Aufgaben, Temperatur 0, ein Durchgang; Ergebnisse je Aufgabe in `lauf<n>/einzeln.jsonl`.", "",
         "| Lauf | Änderung davor | Rückfrage richtig | Vorschlag richtig | Ebene richtig | Beziehung gefunden | "
         "Elemente ohne Fehler | Quelle belegt | Modell gültig (OMG) | Median s |", "|---|---|---|---|---|---|---|---|---|---|"]
    for lauf in sorted(AENDERUNG):
        f = N / lauf / "ergebnisse.json"
        if f.exists():
            e = json.loads(f.read_text(encoding="utf-8"))
            k = e["kennzahlen"]
            z.append(f"| {lauf[-1]} | {AENDERUNG[lauf]} | {k['rueckfrage_richtig']}/{k['rueckfrageaufgaben']} | "
                     f"{k['vorschlag_richtig']}/{k['vorschlagsaufgaben']} | {k['ebene_richtig']}/{k['vorschlagsaufgaben']} | "
                     f"{k['ziele_gefunden']}/{k['ziele_erwartet']} | {k['elemente_ohne_fehler']}/{k['elemente']} | "
                     f"{k['elemente_belegt']}/{k['elemente']} | {k['syntax_ok']}/{k['syntax_geprueft']} | "
                     f"{str(k['dauer_median_s']).replace('.', ',')} |")
        else:
            log = (N / f"{lauf}.log").read_text(encoding="utf-8")
            t = re.findall(r"^([A-D]\d\d): (\w+)\s+(\d+) El\. ok=(\w+) syntax=(\w+)", log, re.M)
            rf, vs = [x for x in t if x[0][0] == "D"], [x for x in t if x[0][0] != "D"]
            syn = [x for x in t if x[4] != "None"]
            z.append(f"| {lauf[-1]} | {AENDERUNG[lauf]} (Abbruch beim Schreiben der Datei; Werte aus `{lauf}.log`) | "
                     f"{sum(x[3] == 'True' for x in rf)}/{len(rf)} | {sum(x[3] == 'True' for x in vs)}/{len(vs)} | – | – | – | – | "
                     f"{sum(x[4] == 'True' for x in syn)}/{len(syn)} | – |")
    z += ["", "„Modell gültig“: Aufgaben, bei denen mindestens ein Element ohne Prüffehler ins Modell eingefügt und das ganze",
          "Modell von der OMG-Pilotimplementierung (jupyter-sysml-kernel) ohne Fehler gelesen wurde.", ""]
    letzte = N / max(AENDERUNG) / "ergebnisse.json"
    if letzte.exists():
        e = json.loads(letzte.read_text(encoding="utf-8"))
        z += ["## Stand des letzten Laufs", "", "```", json.dumps(e["meta"], ensure_ascii=False, indent=1), "```", "",
              "## Fehler im letzten Lauf (je Aufgabe)", ""]
        for r in e["aufgaben"]:
            probleme = []
            if not r["status_richtig"]:
                probleme.append(f"Status {r['status']} statt {r['erwartet']['status']}")
            if r["erwartet"]["status"] == "vorschlag":
                if not r.get("ebene_richtig"):
                    probleme.append(f"Ebene {sorted({x['ebene'] for x in r['elemente']})} statt {r['erwartet']['ebenen']}")
                fehlend = [x for x in r["erwartet"].get("ziele", []) if x not in r.get("ziele_gefunden", [])]
                if fehlend:
                    probleme.append("Beziehung zu " + ", ".join(fehlend) + " fehlt")
            if r.get("syntax") and not r["syntax"]["ok"]:
                probleme.append("Modell ungültig")
            if probleme:
                z.append(f"- **{r['id']}** „{r['eingabe']}“: " + "; ".join(probleme))
    (N / "PROTOKOLL.md").write_text("\n".join(z) + "\n", encoding="utf-8")
    print("\n".join(z[:12]))


if __name__ == "__main__":
    main()
