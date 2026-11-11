"""Oberfläche und REST-Schnittstelle. Nur für den Prototyp: keine Anmeldung, lauscht nur auf 127.0.0.1."""
import re
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import audit
from .config import laden
from .db import verbinden
from .dienst import Dienst
from .llm import Sprachmodell
from .suche import Index
from .wissen import lastenheft

HIER = Path(__file__).parent
app = FastAPI(title="Modellassistent (Prototyp)", version="0.1.0")
app.mount("/static", StaticFiles(directory=HIER / "static"), name="static")
vorlagen = Jinja2Templates(directory=HIER / "templates")
BERLIN = ZoneInfo("Europe/Berlin")
ART = {"R": ("Anforderung", "Neue Anforderung"), "F": ("Funktion", "Neue Funktion"),
       "L": ("Bausteintyp", "Neuer Bausteintyp"), "P": ("Bauteil", "Neues Bauteil")}
STATUS = {"offen": "wartet auf Ihre Prüfung", "rueckfrage": "Rückfrage", "freigegeben": "übernommen",
          "verworfen": "verworfen"}
KLARTEXT = [  # Prüfhinweise in Alltagsdeutsch; der Fachtext bleibt im Protokoll und im Export
    (r"^keine wörtlich belegte Quelle$", "Kein wörtlicher Beleg im Lastenheft gefunden. Bitte selbst prüfen."),
    (r"^Zitat aus (\S+) steht so nicht in der Quelle$", r"Das Zitat steht so nicht in \1. Bitte prüfen."),
    (r"^Quelle (\S+) stand nicht im Kontext$", r"Die Quelle \1 ist unbekannt."),
    (r"^keine Beziehung zu einem Teil des Fahrzeugs.*$", "Noch keinem Bauteil zugeordnet."),
    (r"^Ziel \S+ \((\w+)\) auf das Teil \S+ \((\w+)\) gelegt$", r"Automatisch dem Bauteil \2 zugeordnet."),
    (r"^Beziehung .* nicht übernommen.*$", "Eine unpassende Verknüpfung wurde entfernt."),
    (r"^Typ fehlte; neuer Baustein (\w+) eingesetzt$", r"Bausteintyp \1 ergänzt."),
]


def klartext(text: str) -> str:
    for muster, ersatz in KLARTEXT:
        if re.match(muster, text):
            return re.sub(muster, ersatz, text)
    return text


def zeit(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone(BERLIN).strftime("%d.%m.%Y, %H:%M")
    except (TypeError, ValueError):
        return iso or ""


def modellname(name: str) -> str:
    """qwen3.8:27b → Qwen3.8 (27B) für die Fußzeile."""
    basis, _, groesse = name.partition(":")
    groesse = groesse.split("-")[0].upper()
    return f"{basis[:1].upper()}{basis[1:]}" + (f" ({groesse})" if groesse and groesse != "LATEST" else "")


vorlagen.env.filters.update(klartext=klartext, zeit=zeit)
vorlagen.env.globals.update(ART=ART, STATUS=STATUS)
BEISPIELE = [
    "Das Fahrzeug soll Rampen mit voller Last befahren können.",
    "Bei Rückwärtsfahrt muss auch hinter dem Fahrzeug überwacht werden; ergänze dafür einen zweiten Scanner.",
    "Das FTF soll schneller werden.",
]


@lru_cache
def dienst() -> Dienst:
    e = laden()
    llm = Sprachmodell(e.ollama_url, e.sprachmodell, e.einbettungsmodell, denken=e.denken,
                      einbettung_cpu=e.einbettung_cpu)
    index = Index(lastenheft(e.wissen), llm, e.daten / "einbettungen.json")
    return Dienst(verbinden(e.daten / "modellassistent.sqlite3"), e, llm, index)


@app.get("/", response_class=HTMLResponse)
def start(request: Request):
    d = dienst()
    nr, modell, syntax = d.stand()
    zahl = Counter(e.ebene for e in modell.elemente.values())
    return vorlagen.TemplateResponse(request, "start.html", {
        "anfragen": d.anfragen_liste()[:8], "nr": nr, "zahl": zahl, "beziehungen": len(modell.beziehungen),
        "syntax": syntax, "beispiele": BEISPIELE, "sprachmodell": modellname(d.llm.modell)})


@app.post("/anfrage")
def anfrage_neu(eingabe: str = Form(...)):
    if not eingabe.strip():
        raise HTTPException(400, "Eingabe fehlt")
    return RedirectResponse(f"/anfrage/{dienst().anfragen(eingabe.strip())}", status_code=303)


@app.get("/anfrage/{aid}", response_class=HTMLResponse)
def anfrage_zeigen(request: Request, aid: int, fehler: str = ""):
    d = dienst()
    a = d.anfrage(aid)
    if not a:
        raise HTTPException(404)
    nr, modell, syntax = d.stand()
    namen = {i: (x.ebene, x.name) for i, x in modell.elemente.items()}
    namen |= {e["id"]: (e["ebene"], (e.get("endfassung") or e)["name"]) for e in a["elemente"]}
    offen = sum(1 for e in a["elemente"] if not e["entscheidung"])
    return vorlagen.TemplateResponse(request, "anfrage.html", {
        "a": a, "v": a["vorschlag"], "fehler": fehler, "namen": namen, "offen": offen, "nr": nr, "syntax": syntax,
        "sprachmodell": modellname(d.llm.modell)})


@app.post("/anfrage/{aid}/element/{eid}")
def element_entscheiden(aid: int, eid: str, art: str = Form(...), name: str = Form(""), text: str = Form(""),
                        typ: str = Form(""), ziele: str = Form("")):
    aenderung = {"name": name, "text": text, "typ": typ, "ziele": ziele.replace(";", ",").split(",")} \
        if art == "bearbeitet" else None
    try:
        dienst().entscheiden(aid, eid, art, aenderung)
    except ValueError as f:
        return RedirectResponse(f"/anfrage/{aid}?fehler={f}", status_code=303)
    return RedirectResponse(f"/anfrage/{aid}#{eid}", status_code=303)


@app.post("/anfrage/{aid}/freigeben")
def freigeben(aid: int):
    try:
        dienst().freigeben(aid)
    except ValueError as f:
        return RedirectResponse(f"/anfrage/{aid}?fehler={f}", status_code=303)
    return RedirectResponse(f"/anfrage/{aid}", status_code=303)


@app.get("/modell", response_class=HTMLResponse)
def modell_zeigen(request: Request):
    d = dienst()
    nr, modell, syntax = d.stand()
    gruppen = {k: [e for e in modell.elemente.values() if e.ebene == k] for k in "RFPL"}
    namen = {i: (x.ebene, x.name) for i, x in modell.elemente.items()}
    return vorlagen.TemplateResponse(request, "modell.html", {
        "nr": nr, "m": modell, "syntax": syntax, "gruppen": gruppen, "namen": namen,
        "sprachmodell": modellname(d.llm.modell)})


@app.get("/protokoll", response_class=HTMLResponse)
def protokoll(request: Request):
    d = dienst()
    ok, n, meldung = audit.pruefen(d.con)
    return vorlagen.TemplateResponse(request, "protokoll.html", {
        "ok": ok, "meldung": meldung, "eintraege": list(reversed(audit.exportieren(d.con))),
        "sprachmodell": modellname(d.llm.modell)})


@app.get("/api/anfrage/{aid}/export")
def export(aid: int):
    if not dienst().anfrage(aid):
        raise HTTPException(404)
    return JSONResponse(dienst().export(aid))


@app.get("/api/protokoll")
def protokoll_export():
    d = dienst()
    ok, n, meldung = audit.pruefen(d.con)
    return {"kette_ok": ok, "meldung": meldung, "eintraege": audit.exportieren(d.con)}
