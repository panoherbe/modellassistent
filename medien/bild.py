"""Bildschirmfotos der laufenden Anwendung für README und Angebot (Playwright, Chromium).

    python medien/bild.py <basis-url> <ausgabeordner>
Startseite, dann die Beispielanfrage „zweiter Scanner“: Vorschlag, Entscheidungen (übernehmen, was die Prüfung
bestanden hat, den Rest verwerfen), Übernahme ins Modell, Modell, Nachvollziehen. Dazu der Export als beispiel.json.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASIS, AUS = sys.argv[1].rstrip("/"), Path(sys.argv[2])
EINGABE = "Bei Rückwärtsfahrt muss auch hinter dem Fahrzeug überwacht werden; ergänze dafür einen zweiten Scanner."
AUS.mkdir(parents=True, exist_ok=True)


def ausschnitt(s, oben, unten, datei):
    a, b = s.locator(oben).first.bounding_box(), s.locator(unten).bounding_box()
    s.screenshot(path=str(AUS / datei), full_page=True,
                 clip={"x": a["x"] - 8, "y": a["y"] - 8, "width": a["width"] + 16, "height": b["y"] + b["height"] - a["y"] + 16})


with sync_playwright() as p:
    b = p.chromium.launch()
    s = b.new_page(viewport={"width": 1000, "height": 860}, device_scale_factor=2, locale="de-DE")
    s.set_default_timeout(900_000)  # das große Modell braucht je Vorschlag etwa anderthalb Minuten
    s.goto(BASIS + "/")
    s.fill("textarea[name=eingabe]", EINGABE)
    s.screenshot(path=str(AUS / "start.png"))
    s.click("form.eingabe button")
    s.wait_for_url("**/anfrage/*")
    s.wait_for_load_state("networkidle")
    s.screenshot(path=str(AUS / "vorschlag-ganz.png"), full_page=True)
    karten = s.locator("section.element")
    n = karten.count()
    ausschnitt(s, "section.buehne", f"section.element >> nth={min(n, 2) - 1}" if n else "section.buehne", "vorschlag.png")
    print("Vorschlag:", s.url, n, "Elemente", flush=True)
    for eid in [k.get_attribute("id") for k in karten.all()]:
        karte = s.locator(f"section.element#{eid}")
        ok = karte.locator("form:has(input[value=angenommen]) button:not([disabled])").count()
        art = "angenommen" if ok else "abgelehnt"
        karte.locator(f"form:has(input[value={art}]) button").click()
        s.wait_for_load_state("networkidle")
        print(eid, art, flush=True)
    s.screenshot(path=str(AUS / "entschieden.png"), full_page=True)
    knopf = s.locator("section.abschluss button")
    if knopf.count() and knopf.is_enabled():
        knopf.click()
        s.wait_for_load_state("networkidle")
    s.screenshot(path=str(AUS / "freigegeben.png"))
    nr = s.url.rstrip("/").split("/")[-1].split("#")[0].split("?")[0]
    (AUS / "beispiel.json").write_text(s.request.get(f"{BASIS}/api/anfrage/{nr}/export").text(), encoding="utf-8")
    s.goto(BASIS + "/modell")
    s.screenshot(path=str(AUS / "modell.png"))
    s.goto(BASIS + "/protokoll")
    s.screenshot(path=str(AUS / "protokoll.png"))
    b.close()
