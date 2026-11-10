"""Fachlogik: Anfrage stellen, je Element entscheiden, freigeben (neuer Modellstand), protokollieren.

Ein Vorschlag geht erst nach der menschlichen Freigabe ins Modell. Elemente mit Prüffehlern lassen sich nicht
unverändert annehmen, nur korrigieren oder ablehnen. Jeder Schritt landet im Protokoll mit Modell-, Prompt- und
Quellenstand.
"""
import json
from datetime import datetime, timezone

import httpx

from . import audit, sysml
from .modell import Modell, einfuegen, lesen
from .pruefung import name_normalisieren, pruefen
from .vorschlag import erzeugen
from .wissen import aus_modell


def jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Dienst:
    def __init__(self, con, einstellungen, llm=None, index=None):
        self.con, self.e, self.llm, self.index = con, einstellungen, llm, index
        if not con.execute("SELECT 1 FROM modellstand").fetchone():
            text = einstellungen.basismodell.read_text(encoding="utf-8")
            m = lesen(text)
            con.execute("INSERT INTO modellstand (nr, sha256, text, anfrage_id, syntax, angelegt) VALUES (1,?,?,NULL,?,?)",
                        (m.sha256, text, json.dumps(self.syntax(text)), jetzt()))
            audit.eintragen(con, "modell_geladen", {"stand": 1, "sha256": m.sha256, "elemente": len(m.elemente)})

    # --- Modell -----------------------------------------------------------------------------------------------------
    def stand(self) -> tuple[int, Modell, dict]:
        z = self.con.execute("SELECT * FROM modellstand ORDER BY nr DESC LIMIT 1").fetchone()
        return z["nr"], lesen(z["text"]), json.loads(z["syntax"])

    def syntax(self, text: str) -> dict:
        """Prüfung mit der OMG-Pilotimplementierung (Dienst `pruefer/`); ohne Dienst „nicht geprüft“."""
        if not self.e.pruefer_url:
            return {"geprueft": False, "ok": None, "meldungen": ["Prüfdienst nicht eingerichtet"]}
        try:
            r = httpx.post(f"{self.e.pruefer_url}/pruefen", json={"text": text}, timeout=180)
            r.raise_for_status()
            return {"geprueft": True, **r.json()}
        except httpx.HTTPError as f:
            return {"geprueft": False, "ok": None, "meldungen": [f"Prüfdienst nicht erreichbar: {f}"]}

    # --- Anfrage ----------------------------------------------------------------------------------------------------
    def anfragen(self, eingabe: str, benutzer: str = "demo") -> int:
        nr, modell, _ = self.stand()
        v = erzeugen(eingabe, modell, self.index, self.llm, aus_modell(modell, "ftf.sysml"))
        status = "rueckfrage" if v["status"] == "rueckfrage" else "offen"
        cur = self.con.execute("INSERT INTO anfrage (eingabe, status, vorschlag, modell_stand, angelegt) VALUES (?,?,?,?,?)",
                               (eingabe, status, json.dumps(v, ensure_ascii=False), modell.sha256[:12], jetzt()))
        aid = cur.lastrowid
        for e in v["elemente"]:
            self.con.execute("INSERT INTO element (anfrage_id, id, daten) VALUES (?,?,?)",
                             (aid, e["id"], json.dumps(e, ensure_ascii=False)))
        audit.eintragen(self.con, "vorschlag_erzeugt", {
            "anfrage": aid, "eingabe": eingabe, "status": v["status"], "rueckfragen": v["rueckfragen"],
            "sprachmodell": v["sprachmodell"], "prompt_version": v["prompt_version"], "modellstand": nr,
            "modell_sha256": v["modell_stand"], "dauer_s": v["dauer_s"],
            "quellen": [{"id": q["id"], "datei": q["datei"], "stand": q["stand"]} for q in v["abgerufen"]],
            "elemente": [{"id": e["id"], "ebene": e["ebene"], "name": e["name"], "pruefung": e["pruefung"]}
                         for e in v["elemente"]]}, benutzer)
        return aid

    def anfrage(self, aid: int) -> dict | None:
        z = self.con.execute("SELECT * FROM anfrage WHERE id = ?", (aid,)).fetchone()
        if not z:
            return None
        elemente = []
        for e in self.con.execute("SELECT * FROM element WHERE anfrage_id = ? ORDER BY rowid", (aid,)):
            d = json.loads(e["daten"])
            d.update({"entscheidung": e["entscheidung"],
                      "endfassung": json.loads(e["endfassung"]) if e["endfassung"] else None})
            elemente.append(d)
        return {**dict(z), "vorschlag": json.loads(z["vorschlag"]), "elemente": elemente}

    def anfragen_liste(self) -> list[dict]:
        return [dict(z) for z in self.con.execute("SELECT id, eingabe, status, angelegt FROM anfrage ORDER BY id DESC")]

    # --- Entscheidung je Element ------------------------------------------------------------------------------------
    def entscheiden(self, aid: int, eid: str, art: str, aenderung: dict | None = None, benutzer: str = "demo") -> dict:
        a = self.anfrage(aid)
        if not a or a["status"] != "offen":
            raise ValueError("Anfrage ist nicht offen")
        e = next((x for x in a["elemente"] if x["id"] == eid), None)
        if e is None:
            raise ValueError("Element unbekannt")
        if art == "angenommen" and e["pruefung"] == "fehler":
            raise ValueError("Element hat Prüffehler: bitte korrigieren oder ablehnen")
        end = None
        if art == "bearbeitet":
            end = {k: e[k] for k in ("id", "ebene", "name", "text", "typ", "bezuege", "quellen")}
            end["bezuege_von"] = e.get("bezuege_von", [])
            end["name"] = name_normalisieren(aenderung.get("name", e["name"]), e["ebene"])
            end["text"] = aenderung.get("text", e["text"]).strip()
            if e["ebene"] == "P":
                end["typ"] = name_normalisieren(aenderung.get("typ", e["typ"] or ""), "L")
            if "ziele" in aenderung:
                kind = "satisfy" if e["ebene"] == "R" else "allocate"
                end["bezuege"] = [{"art": kind, "ziel": z.strip().upper()} for z in aenderung["ziele"] if z.strip()]
            _, modell, _ = self.stand()
            andere = [x.get("endfassung") or x for x in a["elemente"] if x["id"] != eid]
            probe = [dict(end)] + [dict(x) for x in andere]
            vorschlag = json.loads(self.con.execute("SELECT vorschlag FROM anfrage WHERE id=?", (aid,)).fetchone()[0])
            kontext = {q["id"]: q for q in vorschlag["abgerufen"]}
            from .wissen import Quelle, aus_modell as _am
            k = {i: Quelle(i, "lastenheft", q["text"], q["datei"], q["stand"]) for i, q in kontext.items()}
            k |= {q.id: q for q in _am(modell, "ftf.sysml")}
            pruefen(probe, modell, k)
            end = probe[0]
            if end["pruefung"] == "fehler":
                raise ValueError("Korrektur hat noch Prüffehler: " + "; ".join(b["text"] for b in end["befunde"]
                                                                              if b["stufe"] == "fehler"))
        self.con.execute("UPDATE element SET entscheidung=?, endfassung=?, entschieden_am=? WHERE anfrage_id=? AND id=?",
                         (art, json.dumps(end, ensure_ascii=False) if end else None, jetzt(), aid, eid))
        audit.eintragen(self.con, "entscheidung", {"anfrage": aid, "element": eid, "entscheidung": art,
                                                   "vorher": {k: e.get(k) for k in ("name", "text", "typ", "bezuege")},
                                                   "nachher": {k: end.get(k) for k in ("name", "text", "typ", "bezuege")}
                                                   if end else None}, benutzer)
        return self.anfrage(aid)

    # --- Freigabe ---------------------------------------------------------------------------------------------------
    def freigeben(self, aid: int, benutzer: str = "demo") -> dict:
        a = self.anfrage(aid)
        if not a or a["status"] != "offen":
            raise ValueError("Anfrage ist nicht offen")
        offen = [e["id"] for e in a["elemente"] if not e["entscheidung"]]
        if offen:
            raise ValueError("Noch nicht entschieden: " + ", ".join(offen))
        frei = [e["endfassung"] or e for e in a["elemente"] if e["entscheidung"] in ("angenommen", "bearbeitet")]
        nr, modell, _ = self.stand()
        if not frei:
            self.con.execute("UPDATE anfrage SET status='verworfen' WHERE id=?", (aid,))
            audit.eintragen(self.con, "verworfen", {"anfrage": aid}, benutzer)
            return {"stand": nr, "neu": False}
        text = einfuegen(modell, sysml.bloecke(frei, modell))
        neu = lesen(text)
        fehlend = [e["id"] for e in frei if e["id"] not in neu.elemente]
        if fehlend:
            raise ValueError("Einfügen fehlgeschlagen für " + ", ".join(fehlend))
        syntax = self.syntax(text)
        self.con.execute("INSERT INTO modellstand (nr, sha256, text, anfrage_id, syntax, angelegt) VALUES (?,?,?,?,?,?)",
                         (nr + 1, neu.sha256, text, aid, json.dumps(syntax, ensure_ascii=False), jetzt()))
        self.con.execute("UPDATE anfrage SET status='freigegeben' WHERE id=?", (aid,))
        audit.eintragen(self.con, "freigegeben", {"anfrage": aid, "stand": nr + 1, "sha256": neu.sha256,
                                                  "elemente": [e["id"] for e in frei], "syntax_ok": syntax.get("ok")},
                        benutzer)
        return {"stand": nr + 1, "neu": True, "syntax": syntax}

    def export(self, aid: int) -> dict:
        """Strukturierte Übergabe: freigegebene Elemente, Beziehungen, Quellen, Stände (für Werkzeuge der Partner)."""
        a = self.anfrage(aid)
        frei = [e["endfassung"] or e for e in a["elemente"] if e["entscheidung"] in ("angenommen", "bearbeitet")]
        z = self.con.execute("SELECT nr, sha256 FROM modellstand WHERE anfrage_id=?", (aid,)).fetchone()
        return {"anfrage": aid, "eingabe": a["eingabe"], "status": a["status"],
                "modellstand": dict(z) if z else None, "sprachmodell": a["vorschlag"]["sprachmodell"],
                "prompt_version": a["vorschlag"]["prompt_version"],
                "elemente": [{k: e.get(k) for k in ("id", "ebene", "name", "text", "typ", "bezuege", "bezuege_von",
                                                     "quellen")} for e in frei],
                "sysml": sysml.vorschau(frei, self.stand()[1]) if frei else ""}
