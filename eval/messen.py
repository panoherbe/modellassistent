"""Messlauf: alle Aufgaben aus eval/aufgaben.yaml durch den Assistenten, Prüfung jedes Vorschlags mit der
OMG-Pilotimplementierung, Ergebnis nach <ausgabe>/ergebnisse.json und PROTOKOLL.md. Jeder Lauf wird aufgehoben.

    docker compose run --rm app python -m eval.messen --ausgabe nachweis/<datum>
"""
import argparse
import json
import os
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from app import sysml
from app.config import PROMPT_VERSION, laden
from app.llm import Sprachmodell
from app.modell import einfuegen, lesen
from app.suche import Index
from app.vorschlag import erzeugen
from app.wissen import aus_modell, lastenheft

HIER = Path(__file__).parent


def ollama_digest(e, name: str) -> str:
    try:
        r = httpx.get(f"{e.ollama_url}/api/tags", timeout=20).json()
        voll = name if ":" in name else name + ":latest"
        return next((m["digest"][:12] for m in r["models"] if m["name"] == voll), "?")
    except Exception:  # noqa: BLE001
        return "?"


def ollama_version(e) -> str:
    try:
        return httpx.get(f"{e.ollama_url}/api/version", timeout=20).json().get("version", "?")
    except Exception:  # noqa: BLE001
        return "?"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ausgabe", required=True, type=Path)
    ap.add_argument("--nur", nargs="*", help="nur diese Aufgaben-IDs")
    a = ap.parse_args(argv)
    e = laden()
    a.ausgabe.mkdir(parents=True, exist_ok=True)
    llm = Sprachmodell(e.ollama_url, e.sprachmodell, e.einbettungsmodell, zeitlimit=900, denken=e.denken,
                       einbettung_cpu=e.einbettung_cpu)
    basis = lesen(e.basismodell.read_text(encoding="utf-8"))
    index = Index(lastenheft(e.wissen), llm, e.daten / "einbettungen.json")
    modellquellen = aus_modell(basis, "ftf.sysml")
    aufgaben = yaml.safe_load((HIER / "aufgaben.yaml").read_text(encoding="utf-8"))
    if a.nur:
        aufgaben = [x for x in aufgaben if x["id"] in a.nur]
    ergebnisse = []
    for t in aufgaben:
        soll = t["erwartet"]
        v = erzeugen(t["eingabe"], basis, index, llm, modellquellen)
        el = v["elemente"]
        ok_el = [x for x in el if x["pruefung"] != "fehler"]
        bezug = {b["ziel"] for x in el for b in x.get("bezuege", [])} | \
                {b["quelle"] for x in el for b in x.get("bezuege_von", [])}
        abgerufen = [q["id"] for q in v["abgerufen"]]
        r = {"id": t["id"], "eingabe": t["eingabe"], "erwartet": soll, "status": v["status"],
             "rueckfragen": v["rueckfragen"], "dauer_s": v["dauer_s"],
             "elemente": [{k: x.get(k) for k in ("id", "ebene", "name", "text", "typ", "bezuege", "bezuege_von",
                                                  "quellen", "pruefung", "befunde")} for x in el],
             "abgerufen": abgerufen, "sysml": v["sysml"]}
        r["status_richtig"] = (v["status"] == soll["status"]) and (soll["status"] == "rueckfrage" or bool(el))
        if soll["status"] == "vorschlag":
            r["ebene_richtig"] = any(x["ebene"] in soll["ebenen"] for x in el)
            r["ziele_gefunden"] = [z for z in soll.get("ziele", []) if z in bezug]
            r["elemente_ohne_fehler"] = len(ok_el)
            r["elemente_belegt"] = sum(1 for x in el if any(q.get("belegt") for q in x.get("quellen", [])))
            rf_el = [x for x in el if x["ebene"] in "RF"]
            r["rf_elemente"] = len(rf_el)
            r["rf_mit_beziehung"] = sum(1 for x in rf_el if x.get("bezuege"))
        r["abruf_treffer"] = [q for q in soll.get("quellen", []) if q in abgerufen]
        if ok_el and e.pruefer_url:
            text = einfuegen(basis, sysml.bloecke(ok_el, basis))
            s = httpx.post(f"{e.pruefer_url}/pruefen", json={"text": text}, timeout=300).json()
            r["syntax"] = {"ok": s["ok"], "meldungen": s["meldungen"][:5], "kernel": s.get("kernel")}
        ergebnisse.append(r)
        with open(a.ausgabe / "einzeln.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{t['id']}: {v['status']:10s} {len(el)} El. ok={r['status_richtig']} "
              f"syntax={r.get('syntax', {}).get('ok')} {v['dauer_s']} s", flush=True)

    vs = [r for r in ergebnisse if r["erwartet"]["status"] == "vorschlag"]
    rf = [r for r in ergebnisse if r["erwartet"]["status"] == "rueckfrage"]
    el_alle = [x for r in vs for x in r["elemente"]]
    ziel_soll = sum(len(r["erwartet"].get("ziele", [])) for r in vs)
    quell_soll = sum(len(r["erwartet"].get("quellen", [])) for r in ergebnisse)
    syn = [r["syntax"]["ok"] for r in ergebnisse if "syntax" in r]
    kennzahlen = {
        "aufgaben": len(ergebnisse), "vorschlagsaufgaben": len(vs), "rueckfrageaufgaben": len(rf),
        "status_richtig": sum(r["status_richtig"] for r in ergebnisse),
        "vorschlag_richtig": sum(r["status_richtig"] for r in vs),
        "rueckfrage_richtig": sum(r["status_richtig"] for r in rf),
        "ebene_richtig": sum(r.get("ebene_richtig", False) for r in vs),
        "ziele_gefunden": sum(len(r.get("ziele_gefunden", [])) for r in vs), "ziele_erwartet": ziel_soll,
        "elemente": len(el_alle), "elemente_ohne_fehler": sum(r.get("elemente_ohne_fehler", 0) for r in vs),
        "elemente_belegt": sum(r.get("elemente_belegt", 0) for r in vs),
        "rf_elemente": sum(r.get("rf_elemente", 0) for r in vs),
        "rf_mit_beziehung": sum(r.get("rf_mit_beziehung", 0) for r in vs),
        "abruf_treffer": sum(len(r["abruf_treffer"]) for r in ergebnisse), "abruf_erwartet": quell_soll,
        "syntax_geprueft": len(syn), "syntax_ok": sum(syn),
        "dauer_median_s": round(statistics.median(r["dauer_s"] for r in ergebnisse), 2),
        "dauer_max_s": max(r["dauer_s"] for r in ergebnisse),
        "ausgabe_tokens_je_s": round(llm.zaehler["ausgabe_tokens"] / llm.zaehler["ausgabe_s"], 1)
        if llm.zaehler["ausgabe_s"] else None,
    }
    try:
        git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        git = ""
    git = git or os.environ.get("CODE_STAND", "?")
    meta = {"zeit_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sprachmodell": e.sprachmodell,
            "sprachmodell_digest": ollama_digest(e, e.sprachmodell), "einbettungsmodell": e.einbettungsmodell,
            "einbettung_digest": ollama_digest(e, e.einbettungsmodell), "denken": e.denken,
            "einbettung_cpu": e.einbettung_cpu,
            "ollama": ollama_version(e), "prompt_version": PROMPT_VERSION,
            "modell_sha256": basis.sha256[:12], "abruf_k": 6, "temperatur": 0, "code": git,
            "kernel": next((r["syntax"].get("kernel") for r in ergebnisse if "syntax" in r), None)}
    (a.ausgabe / "ergebnisse.json").write_text(json.dumps({"meta": meta, "kennzahlen": kennzahlen,
                                                           "aufgaben": ergebnisse}, ensure_ascii=False, indent=1))
    print(json.dumps({"meta": meta, "kennzahlen": kennzahlen}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
