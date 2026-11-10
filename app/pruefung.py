"""Technische Prüfung eines Vorschlags gegen die vereinbarte Struktur, bevor ein Mensch ihn sieht.

Fehler sperren die unveränderte Übernahme (der Mensch muss korrigieren oder ablehnen); Warnungen werden angezeigt.
Geprüft wird: Ebene und Name, Typ eines physischen Teils, jede Beziehung (Art, Richtung, Ziel vorhanden) und jede
Quelle (aus dem gelieferten Kontext und wörtlich belegt).
"""
import re
import unicodedata

from .modell import NAME, Modell
from .wissen import Quelle, belegt

UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}


def name_normalisieren(name: str, ebene: str) -> str:
    """„Ladestation anfahren“ → ladestationAnfahren (L: LadestationAnfahren); ohne Umlaute, nur [A-Za-z0-9_]."""
    for a, b in UMLAUTE.items():
        name = name.replace(a, b)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    teile = [t for t in re.split(r"[^A-Za-z0-9]+", name) if t]
    if not teile:
        return ""
    wort = teile[0] + "".join(t[:1].upper() + t[1:] for t in teile[1:])
    wort = wort[:1].upper() + wort[1:] if ebene == "L" else wort[:1].lower() + wort[1:]
    return wort if not wort[:1].isdigit() else "_" + wort


def pruefen(elemente: list[dict], modell: Modell, kontext: dict[str, Quelle]) -> None:
    """Schreibt je Element `befunde` (Liste von {stufe, text}) und `quellen[i].belegt`; ändert sonst nichts."""
    neu = {e["id"]: e for e in elemente}
    for e in elemente:
        b: list[dict] = []

        def fehler(t):
            b.append({"stufe": "fehler", "text": t})

        def warnung(t):
            b.append({"stufe": "warnung", "text": t})

        if e["ebene"] not in "RFLP" or len(e["ebene"]) != 1:
            fehler(f"Ebene {e['ebene']!r} ist keine RFLP-Ebene")
        if not NAME.match(e.get("name") or ""):
            fehler(f"Name {e.get('name')!r} ist kein gültiger SysML-Name")
        elif modell.nach_name(e["ebene"], e["name"]) or any(
                x is not e and x["ebene"] == e["ebene"] and x["name"] == e["name"] for x in elemente):
            fehler(f"Name {e['name']} gibt es auf Ebene {e['ebene']} schon")
        if not (e.get("text") or "").strip() and e["ebene"] != "P":
            fehler("Beschreibung fehlt")
        if e["ebene"] == "P":
            typ = e.get("typ") or ""
            if not (modell.nach_name("L", typ) or any(x["ebene"] == "L" and x["name"] == typ for x in elemente)):
                fehler(f"Typ {typ!r} ist kein logischer Baustein (L) im Modell oder im Vorschlag")
        for r in e.get("bezuege", []):
            ziel = neu.get(r["ziel"]) or (modell.elemente.get(r["ziel"]).__dict__ if r["ziel"] in modell.elemente else None)
            if ziel is None:
                fehler(f"Beziehung {r['art']} zielt auf {r['ziel']}, das es nicht gibt")
                continue
            paar = {e["ebene"], ziel["ebene"]}
            if r["art"] == "satisfy" and paar != {"R", "P"}:
                fehler(f"satisfy verbindet eine Anforderung (R) mit einem Teil (P), nicht {e['ebene']} mit {ziel['ebene']}")
            if r["art"] == "allocate" and paar != {"F", "P"}:
                fehler(f"allocate verbindet eine Funktion (F) mit einem Teil (P), nicht {e['ebene']} mit {ziel['ebene']}")
        for r in e.get("bezuege_von", []):
            quelle = modell.elemente.get(r["quelle"])
            paar = {e["ebene"], quelle.ebene} if quelle else set()
            if not quelle or (r["art"] == "satisfy" and paar != {"R", "P"}) or (r["art"] == "allocate" and paar != {"F", "P"}):
                fehler(f"Beziehung {r['art']} von {r['quelle']} passt nicht zu Ebene {e['ebene']}")
        for h in e.get("hinweise", []):
            warnung(h)
        if e["ebene"] in "RF" and not e.get("bezuege"):
            warnung("keine Beziehung zu einem Teil des Fahrzeugs (satisfy/allocate)")
        n_belegt = 0
        for q in e.get("quellen", []):
            quelle = kontext.get(q["quelle"])
            q["belegt"] = bool(quelle and belegt(q.get("zitat", ""), quelle))
            if not quelle:
                warnung(f"Quelle {q['quelle']} stand nicht im Kontext")
            elif not q["belegt"]:
                warnung(f"Zitat aus {q['quelle']} steht so nicht in der Quelle")
            n_belegt += q["belegt"]
        if not n_belegt:
            warnung("keine wörtlich belegte Quelle")
        e["befunde"] = b
        e["pruefung"] = "fehler" if any(x["stufe"] == "fehler" for x in b) else ("warnung" if b else "ok")
