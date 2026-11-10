"""Wissensquellen: Absätze des (synthetischen) Lastenhefts und Elemente des Modells, je mit Kennung und Stand.

Jede Quelle trägt die SHA-256 ihrer Datei bzw. des Modells: So steht im Protokoll, aus welchem Stand ein Vorschlag stammt.
"""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .modell import Modell

_ABSATZ = re.compile(r"^(LH-\d+\.\d+)\s+(.+)$", re.M)


@dataclass(frozen=True)
class Quelle:
    id: str           # LH-2.3 oder R-004
    art: str          # "lastenheft" oder "modell"
    text: str
    datei: str
    stand: str        # SHA-256 (Anfang) der Datei bzw. des Modells


def lastenheft(ordner: Path) -> list[Quelle]:
    out = []
    for datei in sorted(ordner.glob("*.md")):
        roh = datei.read_text(encoding="utf-8")
        stand = hashlib.sha256(roh.encode("utf-8")).hexdigest()[:12]
        out += [Quelle(m.group(1), "lastenheft", m.group(2).strip(), datei.name, stand) for m in _ABSATZ.finditer(roh)]
    return out


def aus_modell(modell: Modell, datei: str) -> list[Quelle]:
    stand = modell.sha256[:12]
    return [Quelle(e.id, "modell", f"{e.name}: {e.text}" if e.text else e.name, datei, stand)
            for e in modell.elemente.values()]


def normalisieren(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("„", '"').replace("“", '"').replace("–", "-")).strip().casefold()


def belegt(zitat: str, quelle: Quelle) -> bool:
    """Ein Zitat gilt als belegt, wenn es (ohne Rücksicht auf Leerraum und Groß-/Kleinschreibung) wörtlich in der Quelle
    steht und mindestens 12 Zeichen lang ist."""
    z = normalisieren(zitat).strip(' ."')
    return len(z) >= 12 and z in normalisieren(quelle.text)
