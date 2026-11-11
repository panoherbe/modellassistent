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
    "lauf7": "aktuelle Modellgeneration (11.11.2026): Sprachmodell qwen3.8:27b, Einbettung embeddinggemma-2, "
             "Ollama 0.40.16, Denkmodus aus; Anweisungen unverändert",
    "lauf8": "keine: Wiederholung von Lauf 7 mit Lastprotokoll (`lauf8-last.log`); 24 von 24 Aufgaben mit gleichem Ergebnis",
}


def modellwahl() -> list[str]:
    """Abschnitt „Wahl der Modelle“ aus nachweis/abruf7/abruf.json und nachweis/probe7/*/einzeln.jsonl."""
    z = []
    abruf = N / "abruf7" / "abruf.json"
    if abruf.exists():
        a = json.loads(abruf.read_text(encoding="utf-8"))
        z += ["## Wahl der Modelle (11.11.2026)", "",
              f"Abruf je Einbettungsmodell (`eval/abruf.py`, {a['meta']['aufgaben']} Aufgaben, {a['meta']['absaetze']} "
              f"Lastenheft-Absätze, k = {a['meta']['k']}, Ollama {a['meta']['ollama']}):", "",
              "| Einbettungsmodell | erwartete Absätze unter den abgerufenen | an erster Stelle |", "|---|---|---|"]
        z += [f"| `{m['modell']}` | {m['treffer']}/{m['erwartet']} | {m['an_erster_stelle']} |" for m in a["modelle"]]
        z += ["", "Gewählt: `embeddinggemma-2` (neueste Generation, meiste Treffer an erster Stelle, Apache 2.0)."]
    proben = sorted((N / "probe7").glob("*/einzeln.jsonl")) if (N / "probe7").exists() else []
    if proben:
        z += ["", "Tempo und Denkmodus (3 Aufgaben A01, C01, D01; Sekunden je Aufgabe, Klärung und Vorschlag):", "",
              "| Variante | A01 | C01 | D01 | Ergebnis |", "|---|---|---|---|---|"]
        for f in proben:
            r = {x["id"]: x for x in map(json.loads, f.read_text(encoding="utf-8").splitlines())}
            sek = " | ".join(str(r[i]["dauer_s"]).replace(".", ",") if i in r else "–" for i in ("A01", "C01", "D01"))
            richtig = sum(x["status_richtig"] for x in r.values())
            name = {"qwen3_8_27b": "`qwen3.8:27b` (gewählt)", "qwen3_8_27b-mtp-q4_K_M": "`qwen3.8:27b` mit MTP",
                    "denken": "`qwen3.8:27b` mit Denkmodus"}.get(f.parent.name, f.parent.name)
            z.append(f"| {name} | {sek} | Status {richtig}/{len(r)} richtig |")
        z += ["", "A01 enthält beim ersten Lauf das Laden des Modells. Die MTP-Variante liefert dieselben Antworten und ist "
              "hier kaum schneller (das Modell liegt zu 44 % im Hauptspeicher); der Denkmodus braucht ein Vielfaches der "
              "Zeit. Gewählt: `qwen3.8:27b`, Denkmodus aus. Das Sprachmodell ist austauschbar (`SPRACHMODELL`); "
              "andere Sprachmodelle sind hier nicht gemessen."]
    return z


def main():
    z = ["# Messprotokoll Modellassistent", "",
         "Aufgaben: `eval/aufgaben.yaml` (24, selbst geschrieben, synthetisch: 17 präzise, 7 ungenau oder widersprüchlich).",
         "Je Lauf alle Aufgaben, Temperatur 0, ein Durchgang; Ergebnisse je Aufgabe in `lauf<n>/einzeln.jsonl`.",
         "Läufe 1 bis 6 (10.11.2026): Sprachmodell `qwen2.5:7b-instruct`, Einbettung `bge-m3`. Ab Lauf 7 (11.11.2026): "
         "die aktuelle Modellgeneration, siehe „Wahl der Modelle“.", "",
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
          "Modell von der OMG-Pilotimplementierung (jupyter-sysml-kernel) ohne Fehler gelesen wurde.", "",
          "Lauf 7 lief am 11.11.2026 zwischen 16:13 und 16:21 UTC neben einer anderen Arbeit auf dem Prozessor. Lauf 8",
          "wiederholt ihn ohne Änderung und schreibt die Rechnerlast alle 30 s mit (Lastmittel 9–10 bei 16 Kernen, davon",
          "rund 8 das Sprachmodell selbst): alle 24 Ergebnisse gleich, die Zeiten etwa 10 % länger. Zeitangaben stammen",
          "deshalb aus Lauf 8.", ""]
    z += modellwahl() + [""]
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
