"""Strukturierte Vorschläge (Zwischenrepräsentation) in SysML-v2-Textnotation übersetzen.

Das Sprachmodell schreibt nie SysML-Text: Es liefert JSON nach einem festen Schema; dieser Baustein erzeugt daraus den
Text nach festen Vorlagen. Damit ist der Text für jeden geprüften Vorschlag gleich aufgebaut, und die Prüfung der
OMG-Pilotimplementierung misst die Vorlagen, nicht die Laune des Modells.
"""
from .modell import Modell


def _doc(text: str) -> str:
    return text.replace("*/", "* /").replace("/*", "/ *").strip()


def element(e: dict) -> str:
    """Ein Element (Schlüssel: id, ebene, name, text, typ) als SysML-Text."""
    doc = _doc(e.get("text", ""))
    if e["ebene"] == "R":
        return f"requirement <'{e['id']}'> {e['name']} {{\n    doc /* {doc} */\n}}"
    if e["ebene"] == "F":
        return f"action <'{e['id']}'> {e['name']} {{\n    doc /* {doc} */\n}}"
    if e["ebene"] == "L":
        return f"part def <'{e['id']}'> {e['name']} {{\n    doc /* {doc} */\n}}"
    if e["ebene"] == "P":
        return f"part <'{e['id']}'> {e['name']} : Logik::{e['typ']};"
    raise ValueError(f"unbekannte Ebene {e['ebene']}")


def beziehung(art: str, quelle: str, ziel: str) -> str:
    """quelle/ziel sind qualifizierte Verweise (Element.verweis)."""
    if art == "satisfy":
        return f"satisfy {quelle} by {ziel};"
    if art == "allocate":
        return f"allocate {quelle} to {ziel};"
    raise ValueError(f"unbekannte Beziehung {art}")


def verweis(e: dict) -> str:
    if e["ebene"] == "P":
        return f"Physik::ftf.{e['name']}"
    return {"R": "Anforderungen", "F": "Funktionen", "L": "Logik"}[e["ebene"]] + "::" + e["name"]


def bloecke(elemente: list[dict], modell: Modell) -> dict[str, list[str]]:
    """Alle freigegebenen Elemente und ihre Beziehungen, sortiert nach Einfügemarke."""
    out: dict[str, list[str]] = {"R": [], "F": [], "L": [], "P": [], "V": []}
    neu = {e["id"]: e for e in elemente}
    for e in elemente:
        out[e["ebene"]].append(element(e))
        for b in e.get("bezuege", []):
            ziel = neu.get(b["ziel"])
            if ziel is None and b["ziel"] not in modell.elemente:
                continue  # Ziel wurde abgelehnt oder ist fehlerhaft: Beziehung entfällt
            ziel_ref = verweis(ziel) if ziel else modell.elemente[b["ziel"]].verweis
            out["V"].append(beziehung(b["art"], verweis(e), ziel_ref))
        for b in e.get("bezuege_von", []):
            out["V"].append(beziehung(b["art"], modell.elemente[b["quelle"]].verweis, verweis(e)))
    return out


def vorschau(elemente: list[dict], modell: Modell) -> str:
    """Der Text, der bei Freigabe ins Modell geht, zum Lesen im Vorschlag."""
    teile = []
    for marke, titel in (("R", "Anforderungen"), ("F", "Funktionen"), ("L", "Logik"), ("P", "Physik::ftf"),
                         ("V", "Verknuepfungen")):
        b = bloecke(elemente, modell)[marke]
        if b:
            teile.append(f"// in {titel}\n" + "\n".join(b))
    return "\n\n".join(teile)
