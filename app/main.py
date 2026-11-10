"""Oberfläche und REST-Schnittstelle. Nur für den Prototyp: keine Anmeldung, lauscht nur auf 127.0.0.1."""
from collections import Counter
from functools import lru_cache
from pathlib import Path

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
BEISPIELE = [
    "Das Fahrzeug soll Rampen mit voller Last befahren können.",
    "Bei Rückwärtsfahrt muss auch hinter dem Fahrzeug überwacht werden; ergänze dafür einen zweiten Scanner.",
    "Das FTF soll schneller werden.",
]


@lru_cache
def dienst() -> Dienst:
    e = laden()
    llm = Sprachmodell(e.ollama_url, e.sprachmodell, e.einbettungsmodell)
    index = Index(lastenheft(e.wissen), llm, e.daten / "einbettungen.json")
    return Dienst(verbinden(e.daten / "modellassistent.sqlite3"), e, llm, index)


@app.get("/", response_class=HTMLResponse)
def start(request: Request):
    d = dienst()
    nr, modell, syntax = d.stand()
    zahl = Counter(e.ebene for e in modell.elemente.values())
    return vorlagen.TemplateResponse(request, "start.html", {
        "anfragen": d.anfragen_liste(), "nr": nr, "zahl": zahl, "beziehungen": len(modell.beziehungen),
        "syntax": syntax, "beispiele": BEISPIELE, "sprachmodell": d.llm.modell})


@app.post("/anfrage")
def anfrage_neu(eingabe: str = Form(...)):
    if not eingabe.strip():
        raise HTTPException(400, "Eingabe fehlt")
    return RedirectResponse(f"/anfrage/{dienst().anfragen(eingabe.strip())}", status_code=303)


@app.get("/anfrage/{aid}", response_class=HTMLResponse)
def anfrage_zeigen(request: Request, aid: int, fehler: str = ""):
    a = dienst().anfrage(aid)
    if not a:
        raise HTTPException(404)
    return vorlagen.TemplateResponse(request, "anfrage.html", {"a": a, "v": a["vorschlag"], "fehler": fehler})


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
    nr, modell, syntax = dienst().stand()
    return vorlagen.TemplateResponse(request, "modell.html", {"nr": nr, "m": modell, "syntax": syntax})


@app.get("/protokoll", response_class=HTMLResponse)
def protokoll(request: Request):
    d = dienst()
    ok, n, meldung = audit.pruefen(d.con)
    return vorlagen.TemplateResponse(request, "protokoll.html", {
        "ok": ok, "meldung": meldung, "eintraege": list(reversed(audit.exportieren(d.con)))})


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
