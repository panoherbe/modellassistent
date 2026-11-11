"""Abruf je Einbettungsmodell messen (ohne Sprachmodell): Wie viele der erwarteten Lastenheft-Absätze aus
eval/aufgaben.yaml sind unter den k abgerufenen? Grundlage für die Wahl des Einbettungsmodells.

    docker compose run --rm app python -m eval.abruf --modelle qwen3-embedding:4b embeddinggemma-2 --ausgabe nachweis/abruf
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.config import laden
from app.llm import Sprachmodell
from app.suche import Index
from app.wissen import lastenheft

from .messen import ollama_digest, ollama_version

HIER = Path(__file__).parent


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelle", nargs="+", required=True)
    ap.add_argument("--ausgabe", required=True, type=Path)
    ap.add_argument("-k", type=int, default=6)
    a = ap.parse_args(argv)
    e = laden()
    a.ausgabe.mkdir(parents=True, exist_ok=True)
    aufgaben = yaml.safe_load((HIER / "aufgaben.yaml").read_text(encoding="utf-8"))
    quellen = lastenheft(e.wissen)
    soll = sum(len(t["erwartet"].get("quellen", [])) for t in aufgaben)
    zeilen = []
    for m in a.modelle:
        llm = Sprachmodell(e.ollama_url, "", m)
        t0 = time.perf_counter()
        index = Index(quellen, llm, a.ausgabe / f"cache-{m.replace(':', '_')}.json")
        treffer, erster, je = 0, 0, {}
        for t in aufgaben:
            ids = [q.id for q, _ in index.suchen(t["eingabe"], k=a.k)]
            hit = [q for q in t["erwartet"].get("quellen", []) if q in ids]
            treffer += len(hit)
            erster += bool(t["erwartet"].get("quellen")) and ids[0] in t["erwartet"]["quellen"]
            je[t["id"]] = ids
        z = {"modell": m, "digest": ollama_digest(e, m), "treffer": treffer, "erwartet": soll,
             "an_erster_stelle": erster, "sekunden": round(time.perf_counter() - t0, 1), "abgerufen": je}
        zeilen.append(z)
        print(f"{m}: {treffer}/{soll} unter den {a.k} abgerufenen, {erster} an erster Stelle, {z['sekunden']} s", flush=True)
    meta = {"zeit_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ollama": ollama_version(e),
            "k": a.k, "absaetze": len(quellen), "aufgaben": len(aufgaben)}
    (a.ausgabe / "abruf.json").write_text(json.dumps({"meta": meta, "modelle": zeilen}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
