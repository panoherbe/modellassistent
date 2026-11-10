"""Bildschirmfotos der laufenden Anwendung für die Doku (Playwright, Chromium).

    python medien/bild.py <basis-url> <ausgabeordner>
Stellt die Beispielanfrage „zweiter Scanner“, fotografiert den Vorschlag, nimmt an, gibt frei, fotografiert den Stand.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASIS, AUS = sys.argv[1].rstrip("/"), Path(sys.argv[2])
EINGABE = "Bei Rückwärtsfahrt muss auch hinter dem Fahrzeug überwacht werden; ergänze dafür einen zweiten Scanner."
AUS.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    s = b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2, locale="de-DE")
    s.goto(BASIS + "/")
    s.fill("textarea[name=eingabe]", EINGABE)
    s.click("text=Vorschlag erzeugen")
    s.wait_for_url("**/anfrage/*", timeout=180000)
    s.wait_for_load_state("networkidle")
    s.screenshot(path=str(AUS / "vorschlag.png"), full_page=True)
    print("Vorschlag:", s.url, flush=True)
    for knopf in s.locator("form:has(input[value=angenommen]) button:not([disabled])").all():
        knopf.click()
        s.wait_for_load_state("networkidle")
    if s.locator("text=Freigeben und ins Modell übernehmen").count():
        s.click("text=Freigeben und ins Modell übernehmen")
        s.wait_for_load_state("networkidle")
    s.screenshot(path=str(AUS / "freigegeben.png"), full_page=True)
    s.goto(BASIS + "/protokoll")
    s.screenshot(path=str(AUS / "protokoll.png"), full_page=False)
    b.close()
