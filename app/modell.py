"""Das SysML-v2-Modell: Elemente mit Kennung lesen, Verweise bilden, freigegebene Vorschläge einfügen.

Gelesen wird die Teilmenge der Textnotation, in der `beispiel/ftf.sysml` geschrieben ist (requirement, action,
part def, part, satisfy, allocate mit Kurznamen <'X-nnn'>). Das ist ein Index für den Assistenten, kein allgemeiner
SysML-v2-Parser; die Gültigkeit des ganzen Modells prüft die OMG-Pilotimplementierung (`pruefer/`).
"""
import hashlib
import re
from dataclasses import dataclass, field

EBENEN = {"R": "Anforderung", "F": "Funktion", "L": "logischer Baustein", "P": "physisches Teil"}
PAKET = {"R": "Anforderungen", "F": "Funktionen", "L": "Logik", "P": "Physik"}
ART = {"R": "requirement", "F": "action", "L": "part def", "P": "part"}
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_ELEMENT = re.compile(
    r"^(?P<einzug>\s*)(?P<art>requirement|action|part def|part)\s+<'(?P<id>[RFLP]-\d{3})'>\s+(?P<name>[A-Za-z_]\w*)"
    r"(?:\s*:\s*(?:Logik::)?(?P<typ>[A-Za-z_]\w*))?")
_DOC = re.compile(r"doc\s+/\*\s*(.*?)\s*\*/", re.S)
_SATISFY = re.compile(r"^\s*satisfy\s+Anforderungen::(\w+)\s+by\s+Physik::ftf(?:\.(\w+))?\s*;")
_ALLOCATE = re.compile(r"^\s*allocate\s+Funktionen::(\w+)\s+to\s+Physik::ftf(?:\.(\w+))?\s*;")


@dataclass
class Element:
    id: str
    ebene: str
    name: str
    text: str = ""
    typ: str | None = None          # nur P: Name der Teiledefinition (L)

    @property
    def verweis(self) -> str:
        """Qualifizierter Name, unter dem das Element in Beziehungen steht."""
        if self.ebene == "P":
            return "Physik::ftf" if self.id == "P-001" else f"Physik::ftf.{self.name}"
        return f"{PAKET[self.ebene]}::{self.name}"


@dataclass
class Modell:
    text: str
    elemente: dict[str, Element] = field(default_factory=dict)
    beziehungen: list[tuple[str, str, str]] = field(default_factory=list)   # (art, quelle-id, ziel-id)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def nach_name(self, ebene: str, name: str) -> Element | None:
        return next((e for e in self.elemente.values() if e.ebene == ebene and e.name == name), None)

    def naechste_id(self, ebene: str, vergeben: set[str] = frozenset()) -> str:
        nr = max([int(i[2:]) for i in list(self.elemente) + list(vergeben) if i[0] == ebene] or [0]) + 1
        return f"{ebene}-{nr:03d}"

    def uebersicht(self) -> str:
        """Kurze Liste aller Elemente für den Kontext des Sprachmodells."""
        zeilen = []
        for e in self.elemente.values():
            extra = f" : {e.typ}" if e.typ else ""
            text = e.text
            if e.ebene == "P" and not text:
                typ = self.nach_name("L", e.typ or "")
                text = f"Teil im Fahrzeug; {typ.text}" if typ else "Teil im Fahrzeug"
            zeilen.append(f"{e.id} [{e.ebene}] {e.name}{extra} – {text}")
        for art, q, z in self.beziehungen:
            zeilen.append(f"{art} {q} -> {z}")
        return "\n".join(zeilen)


def lesen(text: str) -> Modell:
    m = Modell(text=text)
    zeilen = text.splitlines()
    for i, zeile in enumerate(zeilen):
        t = _ELEMENT.match(zeile)
        if t:
            ebene = t["id"][0]
            rest = "\n".join(zeilen[i:i + 4])
            doc = _DOC.search(rest) if "{" in zeile else None
            m.elemente[t["id"]] = Element(t["id"], ebene, t["name"], doc.group(1) if doc else "", t["typ"])
    for zeile in zeilen:
        for muster, art, ebene in ((_SATISFY, "satisfy", "R"), (_ALLOCATE, "allocate", "F")):
            b = muster.match(zeile)
            if b:
                quelle = m.nach_name(ebene, b.group(1))
                ziel = m.nach_name("P", b.group(2)) if b.group(2) else m.elemente.get("P-001")
                if quelle and ziel:
                    m.beziehungen.append((art, quelle.id, ziel.id))
    return m


def einfuegen(modell: Modell, bloecke: dict[str, list[str]]) -> str:
    """Freigegebene SysML-Blöcke an den Markierungen „// einfuegen: X“ einsetzen (X = R, F, L, P oder V)."""
    text = modell.text
    for marke, teile in bloecke.items():
        if not teile:
            continue
        muster = re.compile(rf"^(?P<einzug>[ \t]*)// einfuegen: {marke}$", re.M)
        treffer = muster.search(text)
        if not treffer:
            raise ValueError(f"Markierung für {marke} fehlt im Modell")
        einzug = treffer["einzug"]
        neu = "\n".join("\n".join(einzug + z if z else z for z in t.splitlines()) for t in teile)
        text = text[:treffer.start()] + neu + "\n" + text[treffer.start():]
    return text
