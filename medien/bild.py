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
    s.screenshot(path=str(AUS / "vorschlag-ganz.png"), full_page=True)
    oben = s.locator("main section.karte").first.bounding_box()
    sysml = s.locator("section.karte", has=s.locator("h2", has_text="SysML v2 nach Freigabe"))
    unten = sysml.bounding_box() if sysml.count() else s.locator("section.element").last.bounding_box()
    s.screenshot(path=str(AUS / "vorschlag.png"), full_page=True,
                 clip={"x": oben["x"] - 6, "y": oben["y"] - 6, "width": oben["width"] + 12,
                       "height": unten["y"] + unten["height"] - oben["y"] + 12})
    print("Vorschlag:", s.url, flush=True)
    # Entscheidungen wie ein Modellierer: vorhandene Bausteine nutzen, Doppelungen ablehnen. Gilt nur, wenn der Vorschlag
    # genau so aussieht wie beim Messlauf; sonst: alles ohne Fehler annehmen, den Rest ablehnen.
    karten = {k.get_attribute("id"): k.locator(".kopf b").inner_text() for k in s.locator("section.element").all()}
    plan = {"L-009": ("abgelehnt", None), "P-009": ("bearbeitet", {"name": "scannerHinten", "typ": "Sicherheitslaserscanner"}),
            "F-008": ("angenommen", None), "F-009": ("abgelehnt", None)}
    if sorted(karten) != sorted(plan) or "hindernisseErkennenRueckwaerts" not in karten.get("F-009", ""):
        print("Vorschlag weicht ab, Rückfall:", karten, flush=True)
        plan = {}
    for eid in sorted(karten):
        art, aenderung = plan.get(eid, (None, None))
        karte = s.locator(f"section.element#{eid}")
        if art is None:
            art = "angenommen" if karte.locator("form:has(input[value=angenommen]) button:not([disabled])").count() else "abgelehnt"
        if art == "bearbeitet":
            karte.locator("summary", has_text="Korrigieren").click()
            for feld, wert in aenderung.items():
                karte.locator(f"form.korrektur [name={feld}]").fill(wert)
            karte.locator("form.korrektur button").click()
        else:
            karte.locator(f"form:has(input[value={art}]) button").click()
        s.wait_for_load_state("networkidle")
        print(eid, art, flush=True)
    s.screenshot(path=str(AUS / "entschieden.png"), full_page=True)
    if s.locator("text=Freigeben und ins Modell übernehmen").count():
        s.click("text=Freigeben und ins Modell übernehmen")
        s.wait_for_load_state("networkidle")
    s.screenshot(path=str(AUS / "freigegeben.png"), full_page=True)
    nr = s.url.rstrip("/").split("/")[-1].split("#")[0].split("?")[0]
    (AUS / "beispiel.json").write_text(s.request.get(f"{BASIS}/api/anfrage/{nr}/export").text(), encoding="utf-8")
    s.goto(BASIS + "/protokoll")
    s.screenshot(path=str(AUS / "protokoll.png"), full_page=False)
    b.close()
