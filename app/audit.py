"""Protokoll: nur erweiterbar, jeder Eintrag sichert per SHA-256 den vorigen (Hash-Kette).

Eine nachträgliche Änderung an einem Eintrag fällt bei `pruefen()` auf; Trigger verbieten UPDATE und DELETE.
Geheimnisse und Zugangsdaten werden nie protokolliert (es gibt im Prototyp keine).
"""
import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone

START = "0" * 64
_sperre = threading.Lock()


def _hash(vorgaenger: str, nr: int, zeit: str, benutzer, aktion: str, daten: str) -> str:
    roh = json.dumps([vorgaenger, nr, zeit, benutzer, aktion, daten], ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()


def eintragen(con: sqlite3.Connection, aktion: str, daten: dict, benutzer: str | None = None) -> str:
    with _sperre:
        letzter = con.execute("SELECT nr, hash FROM protokoll ORDER BY nr DESC LIMIT 1").fetchone()
        nr = (letzter["nr"] + 1) if letzter else 1
        vorgaenger = letzter["hash"] if letzter else START
        zeit = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        roh = json.dumps(daten, ensure_ascii=False, sort_keys=True)
        h = _hash(vorgaenger, nr, zeit, benutzer, aktion, roh)
        con.execute("INSERT INTO protokoll (nr, zeit, benutzer, aktion, daten, vorgaenger, hash) VALUES (?,?,?,?,?,?,?)",
                    (nr, zeit, benutzer, aktion, roh, vorgaenger, h))
        return h


def pruefen(con: sqlite3.Connection) -> tuple[bool, int, str]:
    vorgaenger, n = START, 0
    for z in con.execute("SELECT * FROM protokoll ORDER BY nr"):
        n += 1
        if z["nr"] != n:
            return False, n, f"Lücke vor Eintrag {z['nr']}"
        if z["vorgaenger"] != vorgaenger:
            return False, n, f"Eintrag {z['nr']}: Verweis auf den Vorgänger stimmt nicht"
        if _hash(z["vorgaenger"], z["nr"], z["zeit"], z["benutzer"], z["aktion"], z["daten"]) != z["hash"]:
            return False, n, f"Eintrag {z['nr']}: Inhalt wurde verändert"
        vorgaenger = z["hash"]
    return True, n, f"{n} Einträge, Kette vollständig"


def exportieren(con: sqlite3.Connection) -> list[dict]:
    """Auswertbarer Export (JSON-Zeilen) aller Einträge, mit geparsten Daten."""
    return [{**dict(z), "daten": json.loads(z["daten"])} for z in con.execute("SELECT * FROM protokoll ORDER BY nr")]
