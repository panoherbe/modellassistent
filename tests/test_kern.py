"""Tests ohne Sprachmodell: Modellindex, Namen, Nachbereitung, Prüfung, SysML-Erzeugung, Einfügen, Protokoll, Ablauf."""
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from app import audit, sysml
from app.config import laden
from app.db import verbinden
from app.dienst import Dienst
from app.modell import einfuegen, lesen
from app.pruefung import name_normalisieren
from app.vorschlag import nachbereiten
from app.wissen import aus_modell, belegt, lastenheft

BASIS = Path(__file__).resolve().parent.parent
MODELL = lesen((BASIS / "modell" / "ftf.sysml").read_text(encoding="utf-8"))
LH = {q.id: q for q in lastenheft(BASIS / "wissen")}
KONTEXT = LH | {q.id: q for q in aus_modell(MODELL, "ftf.sysml")}


def test_modell_index():
    zahl = {e: sum(1 for x in MODELL.elemente.values() if x.ebene == e) for e in "RFLP"}
    assert zahl == {"R": 7, "F": 7, "L": 8, "P": 8}
    assert len(MODELL.beziehungen) == 14
    assert MODELL.elemente["P-004"].typ == "Sicherheitslaserscanner"
    assert MODELL.elemente["P-004"].verweis == "Physik::ftf.scannerVorn"
    assert MODELL.naechste_id("R") == "R-008"


def test_lastenheft():
    assert len(LH) == 20 and LH["LH-2.3"].text.startswith("Rampen in der Halle")


@pytest.mark.parametrize("roh,ebene,soll", [("Ladestation anfahren", "F", "ladestationAnfahren"),
                                            ("Rückfahrscanner", "L", "Rueckfahrscanner"),
                                            ("scanner hinten", "P", "scannerHinten"), ("", "R", "")])
def test_namen(roh, ebene, soll):
    assert name_normalisieren(roh, ebene) == soll


def test_belegt():
    assert belegt("Steigung von höchstens 4 %", LH["LH-2.3"])
    assert not belegt("Steigung von höchstens 6 %", LH["LH-2.3"])
    assert not belegt("4 %", LH["LH-2.3"])  # zu kurz, um etwas zu belegen


ROH = {"status": "vorschlag", "rueckfragen": [], "elemente": [
    {"ebene": "L", "name": "Rückfahrscanner", "text": "Sensor für das Schutzfeld hinter dem Fahrzeug.", "bezuege": [],
     "quellen": [{"quelle": "LH-4.2", "zitat": "das Schutzfeld hinter dem Fahrzeug ebenso überwacht werden"}]},
    {"ebene": "P", "name": "scanner hinten", "typ": "Sicherheitslaserscanner", "text": "",
     "bezuege": [{"art": "satisfy", "ziel": "R-003"}],
     "quellen": [{"quelle": "LH-4.2", "zitat": "Bei Rückwärtsfahrt muss das Schutzfeld hinter dem Fahrzeug"}]},
    {"ebene": "F", "name": "Rückraum überwachen", "text": "Schutzfeld hinter dem Fahrzeug überwachen.",
     "bezuege": [{"art": "allocate", "ziel": "NEU-2"}], "quellen": [{"quelle": "LH-9.9", "zitat": "erfunden"}]},
]}


def test_nachbereiten_und_pruefen():
    v = nachbereiten(json.loads(json.dumps(ROH)), MODELL, KONTEXT)
    ids = [e["id"] for e in v["elemente"]]
    assert ids == ["L-009", "P-009", "F-008"]
    l, p, f = v["elemente"]
    assert l["name"] == "Rueckfahrscanner" and p["name"] == "scannerHinten"
    assert p["bezuege"] == [] and p["bezuege_von"] == [{"art": "satisfy", "quelle": "R-003"}]
    assert f["bezuege"] == [{"art": "allocate", "ziel": "P-009"}]
    assert p["quellen"][0]["belegt"] and not f["quellen"][0]["belegt"]
    assert f["pruefung"] == "warnung" and any("LH-9.9" in b["text"] for b in f["befunde"])
    assert p["pruefung"] == "ok"
    assert "satisfy Anforderungen::personenschutz by Physik::ftf.scannerHinten;" in v["sysml"]
    assert "allocate Funktionen::rueckraumUeberwachen to Physik::ftf.scannerHinten;" in v["sysml"]


def test_fehler_sperren():
    roh = {"status": "vorschlag", "rueckfragen": [], "elemente": [
        {"ebene": "R", "name": "nutzlast", "text": "doppelt", "bezuege": [{"art": "allocate", "ziel": "P-002"}],
         "quellen": []},
        {"ebene": "P", "name": "teil", "typ": "Gibtsnicht", "text": "", "bezuege": [], "quellen": []}]}
    v = nachbereiten(roh, MODELL, KONTEXT)
    r, p = v["elemente"]
    assert r["pruefung"] == "fehler" and any("schon" in b["text"] for b in r["befunde"])
    assert r["bezuege"] == [] and any("nicht übernommen" in b["text"] for b in r["befunde"])
    assert p["pruefung"] == "fehler" and v["sysml"] == ""


def test_typ_aus_neuem_baustein():
    roh = {"status": "vorschlag", "rueckfragen": [], "elemente": [
        {"ebene": "L", "name": "Ladespule", "text": "Spule für kontaktloses Laden.", "bezuege": [], "quellen": []},
        {"ebene": "P", "name": "ladespule", "typ": "", "text": "", "bezuege": [{"art": "satisfy", "ziel": "P-009"}],
         "quellen": []}]}
    l, p = nachbereiten(roh, MODELL, KONTEXT)["elemente"]
    assert p["typ"] == "Ladespule" and p["bezuege"] == [] and p["pruefung"] == "warnung"


def test_l_ziel_wird_teil():
    roh = {"status": "vorschlag", "rueckfragen": [], "elemente": [
        {"ebene": "R", "name": "rampenfaehigkeit", "text": "Rampen bis 4 % mit voller Last.",
         "bezuege": [{"art": "satisfy", "ziel": "L-001"}],
         "quellen": [{"quelle": "LH-2.3", "zitat": "Rampen in der Halle haben eine Steigung von höchstens 4 %"}]}]}
    e = nachbereiten(roh, MODELL, KONTEXT)["elemente"][0]
    assert e["bezuege"] == [{"art": "satisfy", "ziel": "P-002"}] and e["pruefung"] == "warnung"


def test_einfuegen_und_neu_lesen():
    v = nachbereiten(json.loads(json.dumps(ROH)), MODELL, KONTEXT)
    text = einfuegen(MODELL, sysml.bloecke(v["elemente"], MODELL))
    neu = lesen(text)
    assert {"L-009", "P-009", "F-008"} <= set(neu.elemente)
    assert ("satisfy", "R-003", "P-009") in neu.beziehungen and ("allocate", "F-008", "P-009") in neu.beziehungen
    assert sum(z.strip().startswith("// einfuegen:") for z in text.splitlines()) == 5


def test_protokoll_kette(tmp_path):
    con = verbinden(tmp_path / "t.sqlite3")
    for i in range(3):
        audit.eintragen(con, "probe", {"i": i})
    assert audit.pruefen(con)[0]
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("UPDATE protokoll SET daten='{}' WHERE nr=2")
    con.execute("DROP TRIGGER protokoll_nur_anhaengen_u")
    con.execute("UPDATE protokoll SET daten='{\"i\": 9}' WHERE nr=2")
    ok, n, meldung = audit.pruefen(con)
    assert not ok and "Eintrag 2" in meldung


class FalschesModell:
    modell, einbettungsmodell = "probe", "probe"

    def json_antwort(self, system, nutzer, schema):
        return json.loads(json.dumps(ROH)), 0.1


class FalscherIndex:
    def suchen(self, text, k=6):
        return [(LH["LH-4.2"], 0.9), (LH["LH-4.1"], 0.8)]


def test_ablauf(tmp_path):
    e = replace(laden(), daten=tmp_path, pruefer_url="")
    d = Dienst(verbinden(tmp_path / "t.sqlite3"), e, FalschesModell(), FalscherIndex())
    aid = d.anfragen("Rückraum überwachen")
    a = d.anfrage(aid)
    assert a["status"] == "offen" and len(a["elemente"]) == 3
    with pytest.raises(ValueError):
        d.freigeben(aid)  # noch nichts entschieden
    d.entscheiden(aid, "L-009", "abgelehnt")
    d.entscheiden(aid, "P-009", "bearbeitet", {"name": "scannerHinten", "text": "", "typ": "Sicherheitslaserscanner"})
    d.entscheiden(aid, "F-008", "angenommen")
    r = d.freigeben(aid)
    assert r["neu"] and r["stand"] == 2
    nr, modell, syntax = d.stand()
    assert "P-009" in modell.elemente and "L-009" not in modell.elemente and syntax["geprueft"] is False
    x = d.export(aid)
    assert [el["id"] for el in x["elemente"]] == ["P-009", "F-008"]
    ok, n, _ = audit.pruefen(d.con)
    assert ok and n == 6  # geladen, Vorschlag, 3 Entscheidungen, Freigabe
